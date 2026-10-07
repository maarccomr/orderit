from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from typing import Dict, Any, List

db = SQLAlchemy()

class Mesa(db.Model):
    """Modelo para representar las mesas del restaurante."""
    __tablename__ = 'mesas'
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.Integer, unique=True, nullable=False)
    capacidad = db.Column(db.Integer, nullable=False)
    estado = db.Column(db.Enum('libre', 'ocupada', 'reservada', name='estado_mesa'), default='libre', nullable=False)
    pedido_activo_id = db.Column(db.Integer, db.ForeignKey('pedidos.id'), nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convierte la mesa a un diccionario."""
        return {
            'id': self.id,
            'numero': self.numero,
            'capacidad': self.capacidad,
            'estado': self.estado,
            'pedido_activo_id': self.pedido_activo_id
        }

class CategoriaMenu(db.Model):
    """Modelo para representar las categorías del menú (ej: Entrantes, Bebidas)."""
    __tablename__ = 'categorias_menu'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    orden = db.Column(db.Integer, default=0)
    activa = db.Column(db.Boolean, default=True)
    
    # Relación con los items del menú
    items = db.relationship('ItemMenu', backref='categoria', lazy=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convierte la categoría a un diccionario, incluyendo sus items."""
        return {
            'id': self.id,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'orden': self.orden,
            'activa': self.activa,
            'items': [item.to_dict() for item in self.items]
        }

class ItemMenu(db.Model):
    """Modelo para representar los platos y bebidas del menú."""
    __tablename__ = 'items_menu'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    precio = db.Column(db.Float, nullable=False)
    imagen_url = db.Column(db.String(255), nullable=True)
    disponible = db.Column(db.Boolean, default=True)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias_menu.id'), nullable=False)
    tiempo_preparacion_min = db.Column(db.Integer, default=10)

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el item del menú a un diccionario."""
        return {
            'id': self.id,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'precio': self.precio,
            'imagen_url': self.imagen_url,
            'disponible': self.disponible,
            'categoria_id': self.categoria_id,
            'tiempo_preparacion_min': self.tiempo_preparacion_min
        }

class Pedido(db.Model):
    """Modelo para representar un pedido (orden/ticket)."""
    __tablename__ = 'pedidos'
    id = db.Column(db.Integer, primary_key=True)
    mesa_id = db.Column(db.Integer, db.ForeignKey('mesas.id'), nullable=False)
    numero_ticket = db.Column(db.String(20), unique=True, nullable=False)
    estado = db.Column(db.Enum('pendiente', 'preparando', 'listo', 'servido', 'pagado', 'cancelado', name='estado_pedido'), default='pendiente', nullable=False)
    notas = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    subtotal = db.Column(db.Float, default=0.0)
    descuento_porcentaje = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)
    metodo_pago = db.Column(db.String(20), nullable=True) # 'efectivo', 'tarjeta', 'mixto'
    
    # Relaciones
    items = db.relationship('ItemPedido', backref='pedido', cascade='all, delete-orphan', lazy=True)
    mesa = db.relationship('Mesa', backref=db.backref('pedidos_historicos', lazy=True), foreign_keys=[mesa_id])

    @staticmethod
    def generar_numero_ticket() -> str:
        """Genera automáticamente el próximo número de ticket (ej: T-0001)."""
        ultimo_pedido = Pedido.query.order_by(Pedido.id.desc()).first()
        if ultimo_pedido and ultimo_pedido.numero_ticket.startswith('T-'):
            try:
                numero = int(ultimo_pedido.numero_ticket.split('-')[1])
                return f"T-{numero + 1:04d}"
            except ValueError:
                pass
        return "T-0001"

    def calcular_total(self) -> float:
        """Recalcula el subtotal a partir de los items, aplica descuento y devuelve el total."""
        self.subtotal = sum(item.precio_unitario * item.cantidad for item in self.items)
        descuento = self.subtotal * (self.descuento_porcentaje / 100)
        self.total = self.subtotal - descuento
        return self.total

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el pedido a un diccionario, expandiendo sus items."""
        return {
            'id': self.id,
            'mesa_id': self.mesa_id,
            'mesa_numero': self.mesa.numero if self.mesa else None,
            'numero_ticket': self.numero_ticket,
            'estado': self.estado,
            'notas': self.notas,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'subtotal': self.subtotal,
            'descuento_porcentaje': self.descuento_porcentaje,
            'total': self.total,
            'metodo_pago': self.metodo_pago,
            'items': [item.to_dict() for item in self.items]
        }

class ItemPedido(db.Model):
    """Modelo para representar los platos específicos dentro de un pedido."""
    __tablename__ = 'items_pedido'
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedidos.id'), nullable=False)
    item_menu_id = db.Column(db.Integer, db.ForeignKey('items_menu.id'), nullable=False)
    cantidad = db.Column(db.Integer, default=1, nullable=False)
    precio_unitario = db.Column(db.Float, nullable=False)
    notas = db.Column(db.Text, nullable=True)
    estado = db.Column(db.Enum('pendiente', 'preparando', 'listo', name='estado_item_pedido'), default='pendiente', nullable=False)
    
    # Relación con el item del menú
    item_menu = db.relationship('ItemMenu')

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el item del pedido a un diccionario."""
        return {
            'id': self.id,
            'pedido_id': self.pedido_id,
            'item_menu_id': self.item_menu_id,
            'item_nombre': self.item_menu.nombre if self.item_menu else 'Desconocido',
            'cantidad': self.cantidad,
            'precio_unitario': self.precio_unitario,
            'notas': self.notas,
            'estado': self.estado
        }
