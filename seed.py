from models import Mesa, CategoriaMenu, ItemMenu

def seed_database(db):
    """
    Rellena la base de datos con datos iniciales de prueba:
    - 8 mesas con diferentes capacidades.
    - 5 categorías de menú.
    - Varios platos y bebidas típicos de un restaurante español.
    """
    
    # 1. Crear las Mesas
    mesas_data = [
        {'numero': 1, 'capacidad': 2},
        {'numero': 2, 'capacidad': 2},
        {'numero': 3, 'capacidad': 4},
        {'numero': 4, 'capacidad': 4},
        {'numero': 5, 'capacidad': 6},
        {'numero': 6, 'capacidad': 6},
        {'numero': 7, 'capacidad': 8},
        {'numero': 8, 'capacidad': 10},
    ]
    
    for m in mesas_data:
        mesa = Mesa(numero=m['numero'], capacidad=m['capacidad'])
        db.session.add(mesa)
        
    # 2. Crear Categorías
    categorias_nombres = [
        'Entrantes',
        'Platos Principales',
        'Postres',
        'Bebidas',
        'Cafetería'
    ]
    
    categorias = {}
    for i, nombre in enumerate(categorias_nombres):
        cat = CategoriaMenu(nombre=nombre, orden=i)
        db.session.add(cat)
        categorias[nombre] = cat
        
    db.session.flush() # Sincronizar para obtener los IDs de las categorías
    
    # 3. Crear Items del Menú
    items_data = [
        # Entrantes
        {'nombre': 'Croquetas caseras', 'precio': 8.50, 'cat': 'Entrantes'},
        {'nombre': 'Patatas bravas', 'precio': 6.00, 'cat': 'Entrantes'},
        {'nombre': 'Ensalada mixta', 'precio': 7.50, 'cat': 'Entrantes'},
        {'nombre': 'Jamón ibérico', 'precio': 18.00, 'cat': 'Entrantes'},
        {'nombre': 'Gazpacho andaluz', 'precio': 6.50, 'cat': 'Entrantes'},
        
        # Platos Principales
        {'nombre': 'Paella valenciana', 'precio': 14.00, 'cat': 'Platos Principales', 'tiempo': 20},
        {'nombre': 'Solomillo de ternera', 'precio': 19.50, 'cat': 'Platos Principales', 'tiempo': 15},
        {'nombre': 'Lubina a la plancha', 'precio': 16.00, 'cat': 'Platos Principales', 'tiempo': 15},
        {'nombre': 'Pollo al ajillo', 'precio': 12.50, 'cat': 'Platos Principales', 'tiempo': 15},
        {'nombre': 'Risotto de setas', 'precio': 13.00, 'cat': 'Platos Principales', 'tiempo': 20},
        
        # Postres
        {'nombre': 'Tarta de queso', 'precio': 6.50, 'cat': 'Postres', 'tiempo': 5},
        {'nombre': 'Crema catalana', 'precio': 5.50, 'cat': 'Postres', 'tiempo': 5},
        {'nombre': 'Brownie con helado', 'precio': 7.00, 'cat': 'Postres', 'tiempo': 5},
        {'nombre': 'Fruta de temporada', 'precio': 4.50, 'cat': 'Postres', 'tiempo': 5},
        
        # Bebidas
        {'nombre': 'Agua mineral', 'precio': 2.50, 'cat': 'Bebidas', 'tiempo': 2},
        {'nombre': 'Coca-Cola', 'precio': 3.00, 'cat': 'Bebidas', 'tiempo': 2},
        {'nombre': 'Cerveza Estrella', 'precio': 3.50, 'cat': 'Bebidas', 'tiempo': 2},
        {'nombre': 'Vino tinto (copa)', 'precio': 4.50, 'cat': 'Bebidas', 'tiempo': 2},
        {'nombre': 'Sangría (jarra)', 'precio': 12.00, 'cat': 'Bebidas', 'tiempo': 5},
        
        # Cafetería
        {'nombre': 'Café solo', 'precio': 1.80, 'cat': 'Cafetería', 'tiempo': 3},
        {'nombre': 'Café con leche', 'precio': 2.20, 'cat': 'Cafetería', 'tiempo': 3},
        {'nombre': 'Cortado', 'precio': 2.00, 'cat': 'Cafetería', 'tiempo': 3},
        {'nombre': 'Té/Infusión', 'precio': 2.50, 'cat': 'Cafetería', 'tiempo': 3},
        {'nombre': 'Carajillo', 'precio': 3.50, 'cat': 'Cafetería', 'tiempo': 3},
    ]
    
    for item_data in items_data:
        cat_obj = categorias[item_data['cat']]
        item = ItemMenu(
            nombre=item_data['nombre'],
            precio=item_data['precio'],
            categoria_id=cat_obj.id,
            tiempo_preparacion_min=item_data.get('tiempo', 10)
        )
        db.session.add(item)
        
    db.session.commit()
    print("Base de datos sembrada correctamente.")
