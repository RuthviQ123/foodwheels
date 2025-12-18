from app import app, db, Restaurant

with app.app_context():
    # 1. Create the empty database file
    db.create_all()

    # 2. Add the restaurants (Notice the FIXED 'velvet_room.jpg')
    r1 = Restaurant(name='The Velvet Room', description='A modern dining experience.', image_file='velvet_room.jpg', location='Downtown')
    r2 = Restaurant(name='Luxe Dining', description='Classic luxury and fine food.', image_file='luxe.jpg', location='Uptown')
    r3 = Restaurant(name='The Urban Retreat', description='A beautiful spot with outdoor seating.', image_file='urban.jpg', location='Market Street')
    r4 = Restaurant(name='Golden Fork', description='The best traditional food.', image_file='golden.jpg', location='Old Town')
    r5 = Restaurant(name='Spice Garden', description='Authentic flavors and spices.', image_file='spice.jpg', location='East Side')
    r6 = Restaurant(name='Sushi Zen', description='Fresh sushi in a peaceful setting.', image_file='zen.jpg', location='River Walk')
    r7 = Restaurant(name='Bella Napoli', description='Wood-fired pizza and pasta.', image_file='bella.jpg', location='Little Italy')
    r8 = Restaurant(name='The Burger Joint', description='Juicy burgers and shakes.', image_file='joint.jpg', location='Main Avenue')

    # 3. Save it all
    db.session.add_all([r1, r2, r3, r4, r5, r6, r7, r8])
    db.session.commit()
    print("SUCCESS: New database created!")