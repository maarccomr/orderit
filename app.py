import os
from flask import Flask, render_template, jsonify, request, redirect, url_for
from flask_socketio import SocketIO, emit
from datetime import datetime

from config import Config
from models import db, Mesa, CategoriaMenu, ItemMenu, Pedido, ItemPedido
from seed import seed_database

from flask_basicauth import BasicAuth

# Inicialización de SocketIO
socketio = SocketIO()

def create_app() -> Flask:
    """Fábrica de la aplicación Flask."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # --- CONFIGURACIÓN DE SEGURIDAD (BASIC AUTH) ---
    app.config['BASIC_AUTH_USERNAME'] = 'marco'       # Tu usuario
    app.config['BASIC_AUTH_PASSWORD'] = 'sistema2026' # Tu contraseña
    app.config['BASIC_AUTH_FORCE'] = True             # True obliga a pedir clave en TODAS las páginas
    basic_auth = BasicAuth(app)
    # -----------------------------------------------

    # Inicializar extensiones
    db.init_app(app)
    socketio.init_app(app, cors_allowed_origins='*', async_mode='eventlet')

    # Crear base de datos e inyectar datos de prueba en la primera petición
    with app.app_context():
        db.create_all()
        # Sembrar datos si no hay mesas
        if not Mesa.query.first():
            seed_database(db)

    # ==========================================
    # RUTAS (VISTAS)
    # ==========================================
    @app.route('/')
    def index():
        """Redirige al listado de pedidos por defecto."""
        return redirect(url_for('pedidos'))

    @app.route('/menu')
    def menu():
        """Renderiza la vista del menú (catálogo)."""
        return render_template('menu.html')

    @app.route('/pedidos')
    def pedidos():
        """Renderiza la vista principal de pedidos y mesas."""
        return render_template('pedidos.html')

    @app.route('/cocina')
    def cocina():
        """Renderiza el Kitchen Display System (KDS) para la cocina."""
        return render_template('cocina.html')

    @app.route('/caja')
    def caja():
        """Renderiza el Terminal de Punto de Venta (POS) / Caja."""
        return render_template('caja.html')

    # ==========================================
    # API REST
    # ==========================================
    @app.route('/api/menu', methods=['GET'])
    def api_menu():
        """Obtiene todo el menú agrupado por categorías."""
        categorias = CategoriaMenu.query.order_by(CategoriaMenu.orden).all()
        return jsonify([c.to_dict() for c in categorias])

    @app.route('/api/mesas', methods=['GET'])
    def api_mesas():
        """Obtiene todas las mesas y su estado actual."""
        mesas = Mesa.query.order_by(Mesa.numero).all()
        return jsonify([m.to_dict() for m in mesas])

    @app.route('/api/pedidos', methods=['GET'])
    def api_pedidos():
        """Obtiene pedidos activos, filtrando por estado o mesa_id opcionalmente."""
        estado = request.args.get('estado')
        mesa_id = request.args.get('mesa_id', type=int)

        query = Pedido.query
        if estado == 'activo':
            query = query.filter(~Pedido.estado.in_(['pagado', 'cancelado']))
        elif estado:
            query = query.filter_by(estado=estado)
        else:
            query = query.filter(~Pedido.estado.in_(['pagado', 'cancelado']))

        if mesa_id:
            query = query.filter_by(mesa_id=mesa_id)

        pedidos = query.order_by(Pedido.created_at.desc()).all()
        return jsonify([p.to_dict() for p in pedidos])

    @app.route('/api/pedidos/<int:id>', methods=['GET'])
    def api_pedido_detalle(id):
        """Obtiene el detalle completo de un pedido específico."""
        pedido = Pedido.query.get_or_404(id)
        return jsonify(pedido.to_dict())

    @app.route('/api/pedidos/<int:id>/pagar', methods=['POST'])
    def api_pagar_pedido(id):
        """Procesa el pago de un pedido y libera la mesa."""
        pedido = Pedido.query.get_or_404(id)
        datos = request.get_json() or {}
        
        pedido.metodo_pago = datos.get('metodo_pago', 'efectivo')
        if 'descuento_porcentaje' in datos:
            pedido.descuento_porcentaje = float(datos['descuento_porcentaje'])
            
        # Recalcular total con descuento y cambiar estado
        pedido.calcular_total()
        pedido.estado = 'pagado'
        pedido.updated_at = datetime.utcnow()
        
        # Liberar la mesa asociada
        if pedido.mesa:
            pedido.mesa.estado = 'libre'
            pedido.mesa.pedido_activo_id = None
            
        db.session.commit()
        
        # Emitir evento a todos los clientes conectados
        socketio.emit('pedido_pagado', pedido.to_dict())
        return jsonify({'status': 'ok', 'pedido': pedido.to_dict()})

    @app.route('/gestion')
    def gestion():
        """Renderiza el Panel Integral de Gestión y Administración."""
        return render_template('gestion.html')

    # ==========================================
    # API REST DE PRODUCTOS Y CATEGORÍAS (CRUD)
    # ==========================================
    @app.route('/api/items', methods=['GET'])
    def api_items_get():
        """Obtiene la lista plana de todos los productos del menú."""
        items = ItemMenu.query.all()
        resultado = []
        for item in items:
            d = item.to_dict()
            d['categoria_nombre'] = item.categoria.nombre if item.categoria else ''
            resultado.append(d)
        return jsonify(resultado)

    @app.route('/api/items', methods=['POST'])
    def api_item_crear():
        """Crea un nuevo plato o bebida en el menú."""
        datos = request.get_json() or {}
        nombre = datos.get('nombre', '').strip()
        precio = float(datos.get('precio', 0))
        categoria_id = int(datos.get('categoria_id'))
        
        if not nombre or not categoria_id:
            return jsonify({'error': 'Nombre y categoría requeridos'}), 400

        nuevo_item = ItemMenu(
            nombre=nombre,
            descripcion=datos.get('descripcion', '').strip(),
            precio=precio,
            imagen_url=datos.get('imagen_url', '').strip(),
            disponible=bool(datos.get('disponible', True)),
            categoria_id=categoria_id,
            tiempo_preparacion_min=int(datos.get('tiempo_preparacion_min', 10))
        )
        db.session.add(nuevo_item)
        db.session.commit()

        d = nuevo_item.to_dict()
        d['categoria_nombre'] = nuevo_item.categoria.nombre if nuevo_item.categoria else ''
        socketio.emit('menu_actualizado', {'accion': 'creado', 'item': d})
        return jsonify({'status': 'ok', 'item': d}), 201

    @app.route('/api/items/<int:id>', methods=['PUT'])
    def api_item_actualizar(id):
        """Actualiza precios, fotos, descripción o disponibilidad de un producto."""
        item = ItemMenu.query.get_or_404(id)
        datos = request.get_json() or {}

        if 'nombre' in datos:
            item.nombre = datos['nombre'].strip()
        if 'descripcion' in datos:
            item.descripcion = datos['descripcion'].strip()
        if 'precio' in datos:
            item.precio = float(datos['precio'])
        if 'imagen_url' in datos:
            item.imagen_url = datos['imagen_url'].strip()
        if 'disponible' in datos:
            item.disponible = bool(datos['disponible'])
        if 'categoria_id' in datos:
            item.categoria_id = int(datos['categoria_id'])
        if 'tiempo_preparacion_min' in datos:
            item.tiempo_preparacion_min = int(datos['tiempo_preparacion_min'])

        db.session.commit()
        d = item.to_dict()
        d['categoria_nombre'] = item.categoria.nombre if item.categoria else ''
        socketio.emit('menu_actualizado', {'accion': 'actualizado', 'item': d})
        return jsonify({'status': 'ok', 'item': d})

    @app.route('/api/items/<int:id>', methods=['DELETE'])
    def api_item_eliminar(id):
        """Elimina un producto del catálogo."""
        item = ItemMenu.query.get_or_404(id)
        # Si tiene items pedidos históricos, desactivarlo en lugar de romper FK
        tiene_pedidos = ItemPedido.query.filter_by(item_menu_id=id).first()
        if tiene_pedidos:
            item.disponible = False
            db.session.commit()
            socketio.emit('menu_actualizado', {'accion': 'desactivado', 'id': id})
            return jsonify({'status': 'ok', 'mensaje': 'Desactivado por seguridad histórica'})
        
        db.session.delete(item)
        db.session.commit()
        socketio.emit('menu_actualizado', {'accion': 'eliminado', 'id': id})
        return jsonify({'status': 'ok', 'mensaje': 'Eliminado'})

    @app.route('/api/categorias', methods=['POST'])
    def api_categoria_crear():
        """Crea una nueva categoría de menú."""
        datos = request.get_json() or {}
        nombre = datos.get('nombre', '').strip()
        if not nombre:
            return jsonify({'error': 'Nombre requerido'}), 400
        
        max_orden = db.session.query(db.func.max(CategoriaMenu.orden)).scalar() or 0
        cat = CategoriaMenu(
            nombre=nombre,
            descripcion=datos.get('descripcion', '').strip(),
            orden=max_orden + 1,
            activa=True
        )
        db.session.add(cat)
        db.session.commit()
        socketio.emit('menu_actualizado', {'accion': 'categoria_creada', 'categoria': cat.to_dict()})
        return jsonify({'status': 'ok', 'categoria': cat.to_dict()}), 201

    # ==========================================
    # MANEJO DE ERRORES
    # ==========================================
    @app.errorhandler(404)
    def not_found_error(error):
        """Manejador global para error 404."""
        return jsonify({'error': 'Recurso no encontrado'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Manejador global para error 500."""
        db.session.rollback()
        return jsonify({'error': 'Error interno del servidor'}), 500

    return app

# Crear instancia de la aplicación
app = create_app()

# ==========================================
# EVENTOS WEBSOCKET (SOCKET.IO)
# ==========================================
@socketio.on('connect')
def handle_connect():
    """Maneja la conexión de un nuevo cliente."""
    print("Cliente conectado")

@socketio.on('disconnect')
def handle_disconnect():
    """Maneja la desconexión de un cliente."""
    print("Cliente desconectado")

@socketio.on('nuevo_pedido')
def handle_nuevo_pedido(data):
    """Crea un nuevo pedido desde un cliente en tiempo real."""
    try:
        mesa_id = data.get('mesa_id')
        items = data.get('items', [])
        notas_pedido = data.get('notas', '')

        # Crear el pedido
        nuevo_pedido = Pedido(
            mesa_id=mesa_id,
            numero_ticket=Pedido.generar_numero_ticket(),
            notas=notas_pedido
        )
        db.session.add(nuevo_pedido)
        db.session.flush() # Para obtener el ID del pedido

        # Añadir los items al pedido
        for item_data in items:
            item_menu = db.session.get(ItemMenu, item_data['item_menu_id'])
            if item_menu:
                item_pedido = ItemPedido(
                    pedido_id=nuevo_pedido.id,
                    item_menu_id=item_menu.id,
                    cantidad=item_data.get('cantidad', 1),
                    precio_unitario=item_menu.precio,
                    notas=item_data.get('notas', '')
                )
                db.session.add(item_pedido)

        # Calcular totales y actualizar mesa
        nuevo_pedido.calcular_total()
        mesa = db.session.get(Mesa, mesa_id)
        if mesa:
            mesa.estado = 'ocupada'
            mesa.pedido_activo_id = nuevo_pedido.id

        db.session.commit()
        
        # Notificar a todos los clientes (especialmente la cocina)
        socketio.emit('pedido_creado', nuevo_pedido.to_dict())

    except Exception as e:
        db.session.rollback()
        print(f"Error creando pedido: {e}")
        socketio.emit('error', {'mensaje': 'No se pudo crear el pedido'})

@socketio.on('actualizar_estado_pedido')
def handle_actualizar_estado_pedido(data):
    """Actualiza el estado general de un pedido."""
    try:
        pedido_id = data.get('pedido_id')
        nuevo_estado = data.get('estado')
        
        pedido = db.session.get(Pedido, pedido_id)
        if pedido:
            pedido.estado = nuevo_estado
            pedido.updated_at = datetime.utcnow()
            db.session.commit()
            
            socketio.emit('estado_pedido_actualizado', {
                'pedido_id': pedido.id,
                'estado': pedido.estado,
                'updated_at': pedido.updated_at.isoformat()
            })
    except Exception as e:
        db.session.rollback()
        print(f"Error actualizando estado del pedido: {e}")
        socketio.emit('error', {'mensaje': 'Error al actualizar el pedido'})

@socketio.on('actualizar_estado_item')
def handle_actualizar_estado_item(data):
    """Actualiza el estado de un plato específico y comprueba si el pedido está listo."""
    try:
        item_pedido_id = data.get('item_pedido_id')
        nuevo_estado = data.get('estado')
        
        item = db.session.get(ItemPedido, item_pedido_id)
        if item:
            item.estado = nuevo_estado
            db.session.flush()
            
            # Comprobar si todos los items del pedido están listos
            pedido = item.pedido
            todos_listos = all(i.estado == 'listo' for i in pedido.items)
            
            if todos_listos and pedido.estado != 'listo':
                pedido.estado = 'listo'
                pedido.updated_at = datetime.utcnow()
                socketio.emit('estado_pedido_actualizado', {
                    'pedido_id': pedido.id,
                    'estado': pedido.estado,
                    'updated_at': pedido.updated_at.isoformat()
                })
            
            db.session.commit()
            socketio.emit('estado_item_actualizado', {
                'item_pedido_id': item.id,
                'pedido_id': pedido.id,
                'estado': item.estado
            })
    except Exception as e:
        db.session.rollback()
        print(f"Error actualizando estado del item: {e}")
        socketio.emit('error', {'mensaje': 'Error al actualizar el item'})

if __name__ == '__main__':
    # Ejecutar la aplicación con soporte para WebSockets
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
