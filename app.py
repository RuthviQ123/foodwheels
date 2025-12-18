from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func 
from werkzeug.utils import secure_filename
import os
import datetime 

app = Flask(__name__)
app.secret_key = 'this_is_my_food_app' 

# --- Database & Upload Configuration ---
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Define where profile pics live
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'static/profile_pics') 

db = SQLAlchemy(app)

# --- Database Models ---

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    # NEW: Profile Picture Column
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    is_admin = db.Column(db.Boolean, default=False)
    orders = db.relationship('Order', backref='customer', lazy=True)
    bookings = db.relationship('Booking', backref='customer', lazy=True)
    
    def __repr__(self):
        return f'<User {self.email}>'

class FoodItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    tag = db.Column(db.String(50), nullable=False) 
    sub_tag = db.Column(db.String(50), nullable=True) 
    price = db.Column(db.Float, nullable=False)
    image_file = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    order_items = db.relationship('OrderItem', backref='food_item', lazy=True)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_placed = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    total_price = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    items = db.relationship('OrderItem', backref='order', lazy=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(100), nullable=False)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    food_item_id = db.Column(db.Integer, db.ForeignKey('food_item.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price_per_item = db.Column(db.Float, nullable=False)

class Restaurant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(500), nullable=True)
    image_file = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=True)
    bookings = db.relationship('Booking', backref='restaurant', lazy=True)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False)
    booking_date = db.Column(db.String(50), nullable=False)
    booking_time = db.Column(db.String(50), nullable=False)
    party_size = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Confirmed')

# --- Routes ---

@app.route('/')
def home():
    user = session.get('user')
    user_data = None
    if user:
        user_data = User.query.filter_by(email=user).first()
    cuisines = FoodItem.query.filter_by(tag='Category', sub_tag='Cuisine').all()
    desserts = FoodItem.query.filter_by(tag='Category', sub_tag='Dessert').all()
    restaurants = Restaurant.query.all()
    return render_template('home.html', user=user_data, cuisines=cuisines, restaurants=restaurants, desserts=desserts)

# --- USER PROFILE ROUTE (UPDATED) ---
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user' not in session: return redirect(url_for('login'))
    
    current_user = User.query.filter_by(email=session['user']).first()
    
    if request.method == 'POST':
        # Update Text Fields
        current_user.first_name = request.form.get('first_name')
        current_user.last_name = request.form.get('last_name')
        current_user.country = request.form.get('country')
        
        # Update Password (only if typed in)
        new_password = request.form.get('password')
        if new_password:
            current_user.password = new_password
            
        # Handle Image Upload
        if 'profile_picture' in request.files: # Matching your HTML name
            file = request.files['profile_picture']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                # Ensure the directory exists
                if not os.path.exists(app.config['UPLOAD_FOLDER']):
                    os.makedirs(app.config['UPLOAD_FOLDER'])
                
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                current_user.image_file = filename

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))

    # Send current info to the template
    return render_template('profile.html', user=current_user)

# --- ADMIN ROUTES ---
@app.route('/admin')
def admin_panel():
    if 'user' not in session: return redirect(url_for('login'))
    current_user = User.query.filter_by(email=session['user']).first()
    if not current_user or not current_user.is_admin:
        flash('Access Denied. Admins only.', 'error')
        return redirect(url_for('home'))
    items = FoodItem.query.all()
    return render_template('admin.html', user=current_user, items=items)

@app.route('/admin/add_item', methods=['POST'])
def add_item():
    if 'user' not in session: return redirect(url_for('login'))
    current_user = User.query.filter_by(email=session['user']).first()
    if not current_user.is_admin: return redirect(url_for('home'))
    name = request.form.get('name')
    tag = request.form.get('tag')
    sub_tag = request.form.get('sub_tag')
    price = float(request.form.get('price'))
    image_file = request.form.get('image_file')
    new_item = FoodItem(name=name, tag=tag, sub_tag=sub_tag, price=price, image_file=image_file)
    db.session.add(new_item)
    db.session.commit()
    flash(f'{name} added successfully!', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete_item/<int:item_id>')
def delete_item(item_id):
    if 'user' not in session: return redirect(url_for('login'))
    current_user = User.query.filter_by(email=session['user']).first()
    if not current_user.is_admin: return redirect(url_for('home'))
    item = FoodItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash('Item deleted.', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        country = request.form['country']
        existing_user = User.query.filter_by(email=email).first()
        if not existing_user:
            new_user = User(email=email, password=password, first_name=first_name, last_name=last_name, country=country)
            db.session.add(new_user)
            db.session.commit()
            flash('Signup successful!', 'success')
            return redirect(url_for('login'))
        else:
            flash('Email already exists.', 'error')
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and user.password == password:
            session['user'] = user.email
            if user.is_admin:
                return redirect(url_for('admin_panel'))
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password', 'error')
    return render_template('login.html')

@app.route('/category/<category_name>')
def category_page(category_name):
    user_data = None
    if 'user' in session:
        user_data = User.query.filter_by(email=session['user']).first()
    items = FoodItem.query.filter_by(tag=category_name).all()
    return render_template('category_page.html', user=user_data, category_name=category_name, items=items)

@app.route('/item/<int:item_id>')
def item_details(item_id):
    user_data = None
    if 'user' in session:
        user_data = User.query.filter_by(email=session['user']).first()
    item = FoodItem.query.get_or_404(item_id)
    return render_template('item_details.html', user=user_data, item=item)

@app.route('/restaurant/<int:restaurant_id>')
def restaurant_details(restaurant_id):
    user_data = None
    if 'user' in session:
        user_data = User.query.filter_by(email=session['user']).first()
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    return render_template('restaurant_details.html', user=user_data, restaurant=restaurant)

@app.route('/book_table/<int:restaurant_id>', methods=['POST'])
def book_table(restaurant_id):
    if 'user' not in session:
        flash('Login required.', 'error')
        return redirect(url_for('login'))
    user = User.query.filter_by(email=session['user']).first()
    booking_date = request.form.get('booking_date')
    booking_time = request.form.get('booking_time')
    party_size = int(request.form.get('party_size', 1))
    new_booking = Booking(user_id=user.id, restaurant_id=restaurant_id, booking_date=booking_date, booking_time=booking_time, party_size=party_size)
    db.session.add(new_booking)
    db.session.commit()
    return redirect(url_for('booking_success', booking_id=new_booking.id))

@app.route('/booking_success/<int:booking_id>')
def booking_success(booking_id):
    if 'user' not in session: return redirect(url_for('login'))
    user = User.query.filter_by(email=session['user']).first()
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != user.id: return redirect(url_for('home'))
    return render_template('booking_success.html', user=user, booking=booking)

@app.route('/add_to_cart/<int:item_id>', methods=['POST'])
def add_to_cart(item_id):
    if 'user' not in session:
        flash('Login required.', 'error')
        return redirect(url_for('login'))
    item = FoodItem.query.get_or_404(item_id)
    quantity = int(request.form.get('quantity', 1))
    cart = session.get('cart', {})
    item_id_str = str(item_id)
    if item_id_str in cart:
        cart[item_id_str]['quantity'] += quantity
    else:
        cart[item_id_str] = {'name': item.name, 'price': item.price, 'quantity': quantity, 'image_file': item.image_file}
    session['cart'] = cart
    flash(f"{quantity} x {item.name} added!", 'success')
    return redirect(url_for('item_details', item_id=item_id))

@app.route('/order_now/<int:item_id>', methods=['POST'])
def order_now(item_id):
    if 'user' not in session: return redirect(url_for('login'))
    item = FoodItem.query.get_or_404(item_id)
    quantity = int(request.form.get('quantity', 1))
    cart = {str(item_id): {'name': item.name, 'price': item.price, 'quantity': quantity, 'image_file': item.image_file}}
    session['cart'] = cart
    return redirect(url_for('checkout_page'))

@app.route('/cart')
def cart_page():
    if 'user' not in session: return redirect(url_for('login'))
    user_data = User.query.filter_by(email=session['user']).first()
    cart = session.get('cart', {})
    total_price = sum(item['price'] * item['quantity'] for item in cart.values())
    return render_template('cart.html', user=user_data, cart=cart, total_price=total_price)

@app.route('/remove_from_cart/<string:item_id>')
def remove_from_cart(item_id):
    cart = session.get('cart', {})
    cart.pop(item_id, None)
    session['cart'] = cart
    return redirect(url_for('cart_page'))

@app.route('/checkout')
def checkout_page():
    if 'user' not in session: return redirect(url_for('login'))
    user_data = User.query.filter_by(email=session['user']).first()
    cart = session.get('cart', {})
    if not cart: return redirect(url_for('cart_page'))
    total_price = sum(item['price'] * item['quantity'] for item in cart.values())
    return render_template('checkout.html', user=user_data, cart=cart, total_price=total_price)

@app.route('/place_order', methods=['POST'])
def place_order():
    if 'user' not in session: return redirect(url_for('login'))
    user = User.query.filter_by(email=session['user']).first()
    cart = session.get('cart', {})
    if not cart: return redirect(url_for('cart_page'))
    total_price = sum(item['price'] * item['quantity'] for item in cart.values()) + 5.00
    new_order = Order(total_price=total_price, customer=user, name=request.form.get('name'), email=request.form.get('email'), address=request.form.get('address'), city=request.form.get('city'))
    db.session.add(new_order)
    db.session.commit() 
    for item_id, item_data in cart.items():
        db.session.add(OrderItem(order_id=new_order.id, food_item_id=int(item_id), quantity=item_data['quantity'], price_per_item=item_data['price']))
    db.session.commit()
    session.pop('cart', None)
    return redirect(url_for('order_success_page', order_id=new_order.id))

@app.route('/order_success')
def order_success_page():
    if 'user' not in session: return redirect(url_for('login'))
    user_data = User.query.filter_by(email=session['user']).first()
    order = Order.query.get(request.args.get('order_id'))
    if not order or order.user_id != user_data.id: return redirect(url_for('home'))
    return render_template('order_success.html', user=user_data, order=order)

@app.route('/my_orders')
def my_orders():
    if 'user' not in session: return redirect(url_for('login'))
    user_data = User.query.filter_by(email=session['user']).first()
    orders = Order.query.filter_by(user_id=user_data.id).order_by(Order.date_placed.desc()).all()
    return render_template('my_orders.html', user=user_data, orders=orders)

@app.route('/my_bookings')
def my_bookings():
    if 'user' not in session: return redirect(url_for('login'))
    user_data = User.query.filter_by(email=session['user']).first()
    bookings = Booking.query.filter_by(user_id=user_data.id).order_by(Booking.id.desc()).all()
    return render_template('my_bookings.html', user=user_data, bookings=bookings)

@app.route('/search')
def search():
    query = request.args.get('query', '').strip()
    if not query: return redirect(url_for('home'))
    user_data = User.query.filter_by(email=session['user']).first() if 'user' in session else None
    results = FoodItem.query.filter(func.lower(FoodItem.name).like(f"%{query.lower()}%")).all()
    return render_template('search_results.html', user=user_data, query=query, results=results)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

@app.route('/add_test_data')
def add_test_data():
    # 1. FORCE DELETE ALL OLD DATA
    try:
        db.session.query(OrderItem).delete()
        db.session.query(Order).delete()
        db.session.query(Booking).delete()
        db.session.query(Restaurant).delete()
        db.session.query(FoodItem).delete()
        db.session.query(User).delete()
        db.session.commit()
    except:
        db.session.rollback()

    # 2. CREATE ADMIN USER
    admin_user = User(
        email='admin@foodwheels.com', 
        password='admin', 
        first_name='Admin', 
        last_name='User', 
        country='FoodWheels HQ',
        is_admin=True
    )
    db.session.add(admin_user)

    # 3. Add Homepage Category Items
    category_items = [
        FoodItem(name='Fish', tag='Category', sub_tag='Cuisine', price=0, image_file='fish.jpeg'),
        FoodItem(name='Prawns', tag='Category', sub_tag='Cuisine', price=0, image_file='prawns.jpeg'),
        FoodItem(name='Pasta', tag='Category', sub_tag='Cuisine', price=0, image_file='pasta.jpg'),
        FoodItem(name='Biryani', tag='Category', sub_tag='Cuisine', price=0, image_file='biryani.jpg'),
        FoodItem(name='Manchuria', tag='Category', sub_tag='Cuisine', price=0, image_file='manchu.jpg'),
        FoodItem(name='Sushi', tag='Category', sub_tag='Cuisine', price=0, image_file='sushi.jpg'),
        FoodItem(name='Burger', tag='Category', sub_tag='Cuisine', price=0, image_file='burger.jpg'),
        FoodItem(name='Pizza', tag='Category', sub_tag='Cuisine', price=0, image_file='pizza.jpg'),
        FoodItem(name='Noodles', tag='Category', sub_tag='Cuisine', price=0, image_file='noodles.jpg'),
        FoodItem(name='Kebab', tag='Category', sub_tag='Cuisine', price=0, image_file='kebab.jpg'),
        FoodItem(name='Shawarma', tag='Category', sub_tag='Cuisine', price=0, image_file='shawarma.jpg'),
        FoodItem(name='French Fries', tag='Category', sub_tag='Cuisine', price=0, image_file='french.jpg'),
        FoodItem(name='Popcorn', tag='Category', sub_tag='Cuisine', price=0, image_file='popcorn.jpeg'),
        FoodItem(name='Chips', tag='Category', sub_tag='Cuisine', price=0, image_file='potato.jpeg'),
        FoodItem(name='Cheese Cake', tag='Category', sub_tag='Dessert', price=0, image_file='cake.jpg'),
        FoodItem(name='Gulab Jamun', tag='Category', sub_tag='Dessert', price=0, image_file='gulab.jpg'),
        FoodItem(name='Donut', tag='Category', sub_tag='Dessert', price=0, image_file='donut.jpeg'), 
        FoodItem(name='Brownies', tag='Category', sub_tag='Dessert', price=0, image_file='brownies.jpeg'),
        FoodItem(name='Puddings', tag='Category', sub_tag='Dessert', price=0, image_file='pudding.jpeg'),
        FoodItem(name='Cookies', tag='Category', sub_tag='Dessert', price=0, image_file='cookies.jpeg')
    ]
    db.session.add_all(category_items)

    # 4. Add Restaurants
    restaurant_items = [
        Restaurant(name='The Velvet Room', description='A modern dining experience.', image_file='Velvett.jpg', location='Downtown'),
        Restaurant(name='Luxe Dining', description='Classic luxury and fine food.', image_file='luxe.jpg', location='Uptown'),
        Restaurant(name='The Urban Retreat', description='A beautiful spot with outdoor seating.', image_file='urban.jpg', location='Market Street'),
        Restaurant(name='Golden Fork', description='The best traditional food.', image_file='golden.jpg', location='Old Town'),
        Restaurant(name='Spice Garden', description='Authentic flavors and spices.', image_file='spice.jpg', location='East Side'),
        Restaurant(name='Sushi Zen', description='Fresh sushi in a peaceful setting.', image_file='zen.jpg', location='River Walk'),
        Restaurant(name='Bella Napoli', description='Wood-fired pizza and pasta.', image_file='bella.jpg', location='Little Italy'),
        Restaurant(name='The Burger Joint', description='Juicy burgers and shakes.', image_file='joint.jpg', location='Main Avenue')
    ]
    db.session.add_all(restaurant_items)

    # 5. Add Real Menu Items (All categories included)
    menu_items = [
        # Fish Items
        FoodItem(name='Grilled Salmon', tag='Fish', sub_tag='Grilled', price=14.99, image_file='fish1.jpg', description='Fresh Atlantic salmon fillet, grilled to perfection with lemon butter and herbs.'),
        FoodItem(name='Grilled Tuna', tag='Fish', sub_tag='Grilled', price=13.99, image_file='fish2.jpg', description='Thick cut tuna steak seared with olive oil and cracked black pepper.'),
        FoodItem(name='Grilled 3 Piece', tag='Fish', sub_tag='Grilled', price=12.99, image_file='fish3.jpg', description='A platter of three seasonal fish fillets, chargrilled for a smoky flavor.'),
        FoodItem(name='Grilled Catfish', tag='Fish', sub_tag='Grilled', price=11.99, image_file='fish4.jpg', description='Tender catfish marinated in cajun spices and grilled until flaky.'),
        FoodItem(name='Fried Salmon', tag='Fish', sub_tag='Fried', price=13.99, image_file='fish5.jpg', description='Salmon chunks battered in a golden crispy coating, served with tartar sauce.'),
        FoodItem(name='Fried Tuna', tag='Fish', sub_tag='Fried', price=12.99, image_file='fish6.avif', description='Crispy breaded tuna bites, perfect for dipping.'),
        FoodItem(name='Fried 3 Piece', tag='Fish', sub_tag='Fried', price=11.99, image_file='fish7.avif', description='A trio of fried fish delicacies, crunchy on the outside and soft on the inside.'),
        FoodItem(name='Fried Catfish', tag='Fish', sub_tag='Fried', price=10.99, image_file='fish8.avif', description='Southern-style deep fried catfish with a cornmeal crust.'),
        FoodItem(name='Smoked Salmon', tag='Fish', sub_tag='Smoked', price=16.99, image_file='fish9.jpg', description='Premium cold-smoked salmon served with cream cheese and dill.'),
        FoodItem(name='Smoked Tuna', tag='Fish', sub_tag='Smoked', price=15.99, image_file='fish10.jpg', description='Hickory smoked tuna steak with a rich, savory flavor profile.'),
        FoodItem(name='Smoked 3 Piece', tag='Fish', sub_tag='Smoked', price=14.99, image_file='fish11.jpg', description='An assortment of our finest smoked catches of the day.'),
        FoodItem(name='Smoked Catfish', tag='Fish', sub_tag='Smoked', price=13.99, image_file='fish12.jpg', description='Slow-smoked catfish fillet glazed with a sweet and spicy bbq sauce.'),
        
        # Prawns
        FoodItem(name='Prawns Crisps', tag='Prawns', sub_tag='Curry', price=15.99, image_file='prawns.jpeg', description='Ultra-crispy prawns seasoned with sea salt and vinegar.'),
        FoodItem(name='Prawns Fry', tag='Prawns', sub_tag='Curry', price=11.99, image_file='prawns1.jpg', description='Spicy marinated prawns shallow fried with curry leaves and chili.'),
        FoodItem(name='Prawns Dish', tag='Prawns', sub_tag='Curry', price=11.99, image_file='prawns2.jpg', description='A classic prawn stir-fry with bell peppers and onions.'),
        FoodItem(name='Prawns Curry', tag='Prawns', sub_tag='Curry', price=11.99, image_file='prawns3.jpg', description='Juicy prawns simmered in a rich, creamy coconut milk gravy.'),
        FoodItem(name='Prawns Soup', tag='Prawns', sub_tag='Curry', price=11.99, image_file='prawns4.jpg', description='A warm and spicy broth filled with tender prawns and fresh vegetables.'),
        FoodItem(name='Prawns Meal', tag='Prawns', sub_tag='Curry', price=11.99, image_file='prawns5.jpg', description='A complete meal featuring prawn curry, rice, and a side salad.'),
        FoodItem(name='Prawns Strips', tag='Prawns', sub_tag='Curry', price=11.99, image_file='prawns6.jpg', description='Thinly sliced prawn strips battered and fried, served with chili dip.'),
        FoodItem(name='Prawns Pasta', tag='Prawns', sub_tag='Curry', price=11.99, image_file='prawns7.jpg', description='Italian pasta tossed with garlic butter prawns and parsley.'),
        FoodItem(name='Garlic Prawns', tag='Prawns', sub_tag='Curry', price=11.99, image_file='prawns8.jpg', description='Sautéed prawns drenched in a rich roasted garlic butter sauce.'),
        FoodItem(name='Prawns Gravy', tag='Prawns', sub_tag='Curry', price=11.99, image_file='prawns9.jpg', description='Thick, spicy tomato-based gravy with jumbo prawns.'),
        FoodItem(name='Baked Prawns', tag='Prawns', sub_tag='Curry', price=11.99, image_file='prawns10.jpg', description='Oven-baked prawns topped with parmesan cheese and breadcrumbs.'),
        FoodItem(name='Smoked Prawns', tag='Prawns', sub_tag='Curry', price=11.99, image_file='prawns11.jpg', description='Wood-smoked prawns with a distinctive barbecue aroma.'),
        
        # Pasta
        FoodItem(name='Pasta Carbonara', tag='Pasta', sub_tag='Classic', price=10.50, image_file='pasta.jpg', description='Traditional Roman pasta with egg, hard cheese, cured pork, and black pepper.'),
        FoodItem(name='Pesto', tag='Pasta', sub_tag='Classic', price=12.50, image_file='pasta1.jpg', description='Penne pasta coated in a fresh basil, pine nut, and parmesan sauce.'),
        FoodItem(name='White Sauce Pasta', tag='Pasta', sub_tag='Classic', price=11.50, image_file='pasta2.jpg', description='Creamy Alfredo sauce tossed with fettuccine and cracked pepper.'),
        FoodItem(name='Pasta Beans', tag='Pasta', sub_tag='Classic', price=15.00, image_file='pasta3.jpg', description='Hearty pasta mixed with kidney beans and a savory tomato reduction.'),
        FoodItem(name='Egg Pasta', tag='Pasta', sub_tag='Classic', price=14.00, image_file='pasta4.jpg', description='Rich egg noodles stir-fried with vegetables and soy sauce.'),
        FoodItem(name='Spinach Pasta', tag='Pasta', sub_tag='Classic', price=10.50, image_file='pasta5.jpg', description='Healthy green spinach dough pasta served with olive oil and garlic.'),
        FoodItem(name='Spaghetti', tag='Pasta', sub_tag='Classic', price=20.00, image_file='pasta6.jpg', description='Classic spaghetti with a rich bolognese meat sauce.'),
        FoodItem(name='Lasagna', tag='Pasta', sub_tag='Classic', price=20.50, image_file='pasta7.jpg', description='Layers of pasta sheets, meat sauce, and melted mozzarella cheese.'),
        FoodItem(name='Baked Pasta', tag='Pasta', sub_tag='Classic', price=25.50, image_file='pasta8.jpg', description='Oven-baked penne pasta with marinara sauce and a cheesy crust.'),
        FoodItem(name='Cheese Pasta', tag='Pasta', sub_tag='Classic', price=13.50, image_file='pasta9.jpg', description='Macaroni pasta loaded with cheddar, mozzarella, and parmesan.'),
        FoodItem(name='Sauced Pasta', tag='Pasta', sub_tag='Classic', price=19.50, image_file='pasta10.jpg', description='Pasta tossed in a spicy Arrabbiata red chili sauce.'),
        FoodItem(name='Chilli Pasta', tag='Pasta', sub_tag='Classic', price=14.50, image_file='pasta11.jpg', description='Fusion style pasta with green chilies, onions, and bell peppers.'),

        # Biryani
        FoodItem(name='Chicken Mini Biryani', tag='Biryani', sub_tag='Main', price=10.00, image_file='biryani.jpg', description='A smaller portion of our classic aromatic chicken biryani.'),
        FoodItem(name='Chicken Dum Biryani', tag='Biryani', sub_tag='Main', price=12.00, image_file='biryani1.jpg', description='Slow-cooked basmati rice and chicken marinated in exotic spices.'),
        FoodItem(name='Chicken Fry Biryani', tag='Biryani', sub_tag='Main', price=15.00, image_file='biryani2.jpg', description='Spicy fried chicken pieces served atop flavorful biryani rice.'),
        FoodItem(name='Chicken Roasted Biryani', tag='Biryani', sub_tag='Main', price=20.00, image_file='biryani3.jpg', description='Tandoori roasted chicken served with saffron-infused rice.'),
        FoodItem(name='Chicken Smoked Biryani', tag='Biryani', sub_tag='Main', price=18.00, image_file='biryani4.jpg', description='Charcoal-smoked chicken biryani with a deep, earthy flavor.'),
        FoodItem(name='Mughal Chicken Biryani', tag='Biryani', sub_tag='Main', price=14.00, image_file='biryani5.jpg', description='A rich, mild biryani cooked with nuts, raisins, and cream.'),
        FoodItem(name='Chicken BBQ Biryani', tag='Biryani', sub_tag='Main', price=18.00, image_file='biryani6.jpg', description='Smoky BBQ chicken wings paired with spicy biryani rice.'),
        FoodItem(name='Classic Chicken Biryani', tag='Biryani', sub_tag='Main', price=35.00, image_file='biryani7.jpg', description='The original Hyderabad recipe with bone-in chicken and spices.'),
        FoodItem(name='Pot Biryani', tag='Biryani', sub_tag='Main', price=30.00, image_file='biryani8.jpg', description='Cooked and served in a clay pot to retain authentic flavors.'),
        FoodItem(name='Special Chicken Biryani', tag='Biryani', sub_tag='Main', price=25.00, image_file='biryani9.jpg', description='Boneless chicken breast pieces in a special masala rice mix.'),
        FoodItem(name='Bamboo Chicken Biryani', tag='Biryani', sub_tag='Main', price=22.00, image_file='biryani10.jpg', description='Unique biryani steamed inside a bamboo shoot for distinct aroma.'),
        FoodItem(name='Chicken Family Biryani', tag='Biryani', sub_tag='Main', price=40.00, image_file='biryani11.jpg', description='A massive platter of biryani suitable for 3-4 people.'),
        
        # Manchuria
        FoodItem(name='Veg Manchuria', tag='Manchuria', sub_tag='Dry', price=9.99, image_file='manchu.jpg', description='Crispy deep-fried vegetable balls tossed in a spicy, sweet, and tangy soy-based sauce.'),
        FoodItem(name='Gobi Manchuria', tag='Manchuria', sub_tag='Dry', price=10.50, image_file='manchu1.jpg', description='Cauliflower florets battered, fried until golden, and coated in zesty manchurian sauce.'),
        FoodItem(name='Paneer Manchuria', tag='Manchuria', sub_tag='Dry', price=12.99, image_file='manchu2.jpg', description='Soft cubes of cottage cheese tossed with bell peppers, onions, and spicy Chinese herbs.'),
        FoodItem(name='Chicken Manchuria', tag='Manchuria', sub_tag='Gravy', price=13.50, image_file='manchu3.jpg', description='Juicy chicken chunks cooked in a rich, savory brown garlic and chili gravy.'),
        FoodItem(name='Baby Corn Manchuria', tag='Manchuria', sub_tag='Appetizer', price=11.50, image_file='manchu4.jpg', description='Crunchy baby corn pieces stir-fried with ginger, garlic, and spring onions.'),
        FoodItem(name='Mushroom Manchuria', tag='Manchuria', sub_tag='Appetizer', price=11.99, image_file='manchu5.jpg', description='Fresh mushrooms battered and sautéed in a spicy, tangy sauce with a hint of vinegar.'),
        FoodItem(name='Soya Chunks Manchuria', tag='Manchuria', sub_tag='Healthy', price=10.99, image_file='manchu6.jpg', description='Protein-packed soya chunks marinated and cooked in traditional Indo-Chinese spices.'),
        FoodItem(name='Wet Veg Manchuria', tag='Manchuria', sub_tag='Gravy', price=10.50, image_file='manchu7.jpg', description='Vegetable balls served in a thick, delicious gravy perfect for eating with fried rice.'),
        FoodItem(name='Pepper Manchuria', tag='Manchuria', sub_tag='Spicy', price=10.99, image_file='manchu8.jpg', description='A spicy twist on the classic, heavily seasoned with crushed black pepper and curry leaves.'),
        FoodItem(name='Schezwan Manchuria', tag='Manchuria', sub_tag='Spicy', price=11.50, image_file='manchu9.jpg', description='Tossed in fiery red Schezwan sauce for those who love an extra kick of heat.'),
        FoodItem(name='Egg Manchuria', tag='Manchuria', sub_tag='Protein', price=11.00, image_file='manchu10.jpg', description='Boiled egg wedges battered and fried, then tossed in a sticky garlic sauce.'),
        FoodItem(name='Mixed Veg Manchuria', tag='Manchuria', sub_tag='Special', price=12.50, image_file='manchu11.jpg', description='A colorful mix of seasonal vegetables fried crisp and glazed with our secret sauce.'),

        # Sushi
        FoodItem(name='California Roll', tag='Sushi', sub_tag='Maki', price=8.99, image_file='sushi.jpg', description='Classic inside-out roll with crab meat, creamy avocado, and crisp cucumber.'),
        FoodItem(name='Salmon Nigiri', tag='Sushi', sub_tag='Nigiri', price=10.99, image_file='sushi1.jpg', description='Slices of fresh, raw salmon draped over vinegared rice.'),
        FoodItem(name='Tuna Sashimi', tag='Sushi', sub_tag='Sashimi', price=12.50, image_file='sushi2.jpg', description='Premium grade raw tuna slices served fresh without rice.'),
        FoodItem(name='Dragon Roll', tag='Sushi', sub_tag='Special', price=14.99, image_file='sushi3.jpg', description='Eel and cucumber roll topped with thinly sliced avocado and eel sauce.'),
        FoodItem(name='Spicy Tuna Roll', tag='Sushi', sub_tag='Maki', price=9.50, image_file='sushi4.jpg', description='Minced fresh tuna mixed with spicy mayo and cucumber, wrapped in seaweed.'),
        FoodItem(name='Shrimp Tempura', tag='Sushi', sub_tag='Fried', price=11.50, image_file='sushi5.jpg', description='Crispy deep-fried shrimp rolled with avocado and drizzled with teriyaki sauce.'),
        FoodItem(name='Rainbow Roll', tag='Sushi', sub_tag='Special', price=13.99, image_file='sushi6.jpg', description='A California roll topped with an assortment of fresh sashimi fish and avocado.'),
        FoodItem(name='Philadelphia Roll', tag='Sushi', sub_tag='Maki', price=9.99, image_file='sushi7.jpg', description='Smoked salmon, cream cheese, and cucumber wrapped in sushi rice.'),
        FoodItem(name='Unagi Nigiri', tag='Sushi', sub_tag='Nigiri', price=11.99, image_file='sushi8.jpg', description='Grilled freshwater eel glazed with sweet soy sauce over a bed of rice.'),
        FoodItem(name='Avocado Maki', tag='Sushi', sub_tag='Veg', price=7.50, image_file='sushi9.jpg', description='Simple and refreshing roll filled with ripe, buttery avocado slices.'),
        FoodItem(name='Sushi Platter', tag='Sushi', sub_tag='Special', price=24.99, image_file='sushi10.jpg', description='A chef’s selection of our finest nigiri, maki, and sashimi (12 pieces).'),
        FoodItem(name='Salmon Temaki', tag='Sushi', sub_tag='Handroll', price=8.50, image_file='sushi11.jpg', description='Cone-shaped hand roll filled with fresh salmon, avocado, and sushi rice.'),
        
        # Burger
        FoodItem(name='Classic Cheeseburger', tag='Burger', sub_tag='Beef', price=9.99, image_file='burger.jpg', description='Juicy beef patty topped with melted cheddar cheese, lettuce, tomato, and pickles.'),
        FoodItem(name='Chicken Burger', tag='Burger', sub_tag='Chicken', price=8.99, image_file='burger1.jpg', description='Crispy fried chicken breast served with mayo and fresh lettuce on a toasted bun.'),
        FoodItem(name='Bacon Double Cheese', tag='Burger', sub_tag='Beef', price=12.99, image_file='burger2.jpg', description='Two beef patties stacked with crispy smoked bacon and double American cheese.'),
        FoodItem(name='Veggie Bean Burger', tag='Burger', sub_tag='Veg', price=9.50, image_file='burger3.jpg', description='A hearty spiced black bean and corn patty served with avocado and salsa.'),
        FoodItem(name='BBQ Brisket Burger', tag='Burger', sub_tag='Special', price=13.99, image_file='burger4.jpg', description='Slow-cooked pulled beef brisket smothered in smoky BBQ sauce and coleslaw.'),
        FoodItem(name='Mushroom Swiss', tag='Burger', sub_tag='Beef', price=11.50, image_file='burger5.jpg', description='Grilled beef patty topped with sautéed mushrooms and melted Swiss cheese.'),
        FoodItem(name='Spicy Jalapeño', tag='Burger', sub_tag='Spicy', price=10.99, image_file='burger6.jpg', description='Packed with heat! Topped with sliced jalapeños, pepper jack cheese, and spicy mayo.'),
        FoodItem(name='Fish Fillet Burger', tag='Burger', sub_tag='Seafood', price=9.99, image_file='burger7.jpg', description='Golden battered fish fillet with tartare sauce and cheese on a soft steamed bun.'),
        FoodItem(name='Crispy Onion Burger', tag='Burger', sub_tag='Beef', price=11.99, image_file='burger8.jpg', description='Topped with a mountain of crispy fried onion rings and tangy steak sauce.'),
        FoodItem(name='Egg & Cheese Burger', tag='Burger', sub_tag='Breakfast', price=10.50, image_file='burger9.jpg', description='Beef patty topped with a sunny-side-up fried egg and caramelized onions.'),
        FoodItem(name='Paneer Tikka Burger', tag='Burger', sub_tag='Veg', price=10.99, image_file='burger10.jpg', description='Grilled paneer slice marinated in tandoori spices, served with mint chutney.'),
        FoodItem(name='Monster Tower', tag='Burger', sub_tag='Special', price=15.99, image_file='burger11.jpg', description='The ultimate challenge: 3 patties, bacon, cheese, onion rings, and special sauce.'),

        # Pizza
        FoodItem(name='Pepperoni Pizza', tag='Pizza', sub_tag='Classic', price=12.99, image_file='pizza.jpg', description='Classic hand-tossed pizza topped with tomato sauce, mozzarella, and generous pepperoni slices.'),
        FoodItem(name='Margherita Pizza', tag='Pizza', sub_tag='Veg', price=10.99, image_file='pizza1.jpg', description='Simple and authentic: San Marzano tomato sauce, fresh mozzarella, basil, and olive oil.'),
        FoodItem(name='BBQ Chicken Pizza', tag='Pizza', sub_tag='Special', price=13.50, image_file='pizza2.jpg', description='Smokey BBQ sauce base topped with grilled chicken, red onions, and cilantro.'),
        FoodItem(name='Veggie Supreme', tag='Pizza', sub_tag='Veg', price=11.99, image_file='pizza3.jpg', description='Loaded with bell peppers, onions, mushrooms, olives, and spinach for a healthy crunch.'),
        FoodItem(name='Hawaiian Pizza', tag='Pizza', sub_tag='Classic', price=12.50, image_file='pizza4.jpg', description='The controversial classic: Sweet pineapple chunks paired with savory ham and cheese.'),
        FoodItem(name='Meat Lovers', tag='Pizza', sub_tag='Special', price=14.99, image_file='pizza5.jpg', description='A carnivore’s dream with pepperoni, sausage, bacon, ham, and ground beef.'),
        FoodItem(name='Buffalo Chicken', tag='Pizza', sub_tag='Spicy', price=13.00, image_file='pizza6.jpg', description='Spicy buffalo sauce base with chicken, mozzarella, and a drizzle of ranch dressing.'),
        FoodItem(name='Mushroom Truffle', tag='Pizza', sub_tag='Gourmet', price=15.50, image_file='pizza7.jpg', description='Earthy wild mushrooms, truffle oil, and thyme on a creamy white garlic sauce base.'),
        FoodItem(name='Four Cheese', tag='Pizza', sub_tag='Cheese', price=12.00, image_file='pizza8.jpg', description='A rich blend of Mozzarella, Cheddar, Parmesan, and Gorgonzola cheeses.'),
        FoodItem(name='Mexican Pizza', tag='Pizza', sub_tag='Spicy', price=13.50, image_file='pizza9.jpg', description='Topped with spicy ground beef, jalapeños, corn, and beans, finished with taco seasoning.'),
        FoodItem(name='Pesto Chicken', tag='Pizza', sub_tag='Gourmet', price=13.99, image_file='pizza10.jpg', description='Fresh basil pesto base topped with grilled chicken strips and sun-dried tomatoes.'),
        FoodItem(name='Chicago Deep Dish', tag='Pizza', sub_tag='Special', price=16.99, image_file='pizza11.jpg', description='Thick, buttery crust filled with layers of cheese, meat, and chunky tomato sauce.'),

        # Noodles
        FoodItem(name='Hakka Noodles', tag='Noodles', sub_tag='Stir-fry', price=9.50, image_file='noodles.jpg', description='Classic stir-fried noodles tossed with julienned vegetables and savory soy sauce.'),
        FoodItem(name='Schezwan Noodles', tag='Noodles', sub_tag='Spicy', price=10.50, image_file='noodles1.jpg', description='Spicy and bold noodles tossed in fiery red Schezwan sauce with garlic and chilies.'),
        FoodItem(name='Veg Chow Mein', tag='Noodles', sub_tag='Classic', price=9.99, image_file='noodles2.jpg', description='Street-style noodles wok-tossed with crunchy cabbage, carrots, and bell peppers.'),
        FoodItem(name='Singapore Noodles', tag='Noodles', sub_tag='Special', price=11.50, image_file='noodles3.jpg', description='Thin rice vermicelli stir-fried with mild curry powder, turmeric, and vegetables.'),
        FoodItem(name='Spicy Ramen', tag='Noodles', sub_tag='Soup', price=12.99, image_file='noodles4.jpg', description='A rich, piping hot broth served with wheat noodles, soft-boiled egg, and nori.'),
        FoodItem(name='Pad Thai', tag='Noodles', sub_tag='Thai', price=11.99, image_file='noodles5.jpg', description='Rice noodles stir-fried with peanuts, bean sprouts, and tamarind pulp sauce.'),
        FoodItem(name='Garlic Butter Noodles', tag='Noodles', sub_tag='Simple', price=8.99, image_file='noodles6.jpg', description='Simple yet delicious noodles tossed in roasted garlic butter and parsley.'),
        FoodItem(name='Chicken Egg Noodles', tag='Noodles', sub_tag='Non-Veg', price=11.50, image_file='noodles7.jpg', description='Savory noodles stir-fried with scrambled eggs and tender chicken strips.'),
        FoodItem(name='Chilli Garlic Noodles', tag='Noodles', sub_tag='Spicy', price=10.50, image_file='noodles8.jpg', description='A pungent and spicy delight loaded with burnt garlic and red chili flakes.'),
        FoodItem(name='Pan Fried Noodles', tag='Noodles', sub_tag='Crispy', price=12.50, image_file='noodles9.jpg', description='Crispy noodle cake topped with a generous ladle of savory vegetable gravy.'),
        FoodItem(name='Teriyaki Udon', tag='Noodles', sub_tag='Japanese', price=13.00, image_file='noodles10.jpg', description='Thick, chewy Japanese udon noodles glazed in a sweet and sticky teriyaki sauce.'),
        FoodItem(name='Dan Dan Noodles', tag='Noodles', sub_tag='Sichuan', price=12.99, image_file='noodles11.jpg', description='Sichuan noodles served in a spicy sauce containing preserved vegetables and chili oil.'),

        # Kebab
        FoodItem(name='Chicken Kebab', tag='Kebab', sub_tag='Grilled', price=11.50, image_file='kebab.jpg', description='Skewered chicken cubes marinated in yogurt and spices, grilled to char perfection.'),
        FoodItem(name='Seekh Kebab', tag='Kebab', sub_tag='Minced', price=12.99, image_file='kebab1.jpg', description='Minced lamb mixed with onions, herbs, and spices, molded onto skewers and grilled.'),
        FoodItem(name='Doner Kebab', tag='Kebab', sub_tag='Turkish', price=10.99, image_file='kebab2.jpg', description='Thinly sliced rotisserie meat served in pita bread with fresh salad and garlic sauce.'),
        FoodItem(name='Galouti Kebab', tag='Kebab', sub_tag='Special', price=13.50, image_file='kebab3.jpg', description='A Lucknowi delicacy of ultra-soft minced meat patties that melt in your mouth.'),
        FoodItem(name='Shami Kebab', tag='Kebab', sub_tag='Classic', price=11.00, image_file='kebab4.jpg', description='A blend of minced meat and chickpeas, flavored with spices and pan-fried.'),
        FoodItem(name='Reshmi Kebab', tag='Kebab', sub_tag='Creamy', price=12.50, image_file='kebab5.jpg', description='Boneless chicken marinated in a silky mixture of cream, cashew paste, and cheese.'),
        FoodItem(name='Hara Bhara Kebab', tag='Kebab', sub_tag='Veg', price=9.99, image_file='kebab6.jpg', description='Healthy and delicious green patties made with spinach, peas, and potatoes.'),
        FoodItem(name='Lamb Shish Kebab', tag='Kebab', sub_tag='Grilled', price=14.50, image_file='kebab7.jpg', description='Tender chunks of leg of lamb marinated in olive oil and lemon, grilled with peppers.'),
        FoodItem(name='Paneer Tikka', tag='Kebab', sub_tag='Veg', price=11.99, image_file='kebab8.jpg', description='Marinated cottage cheese cubes grilled in a tandoor with onions and bell peppers.'),
        FoodItem(name='Adana Kebab', tag='Kebab', sub_tag='Turkish', price=13.99, image_file='kebab9.jpg', description='Spicy hand-minced meat mounted on a wide iron skewer and grilled over charcoal.'),
        FoodItem(name='Malai Kebab', tag='Kebab', sub_tag='Creamy', price=12.99, image_file='kebab10.jpg', description='Mild and creamy chicken kebabs flavored with ginger, garlic, and green cardamom.'),
        FoodItem(name='Mixed Platter', tag='Kebab', sub_tag='Special', price=18.99, image_file='kebab11.jpg', description='The ultimate feast featuring a variety of chicken, lamb, and seafood kebabs.'),

        # Shawarma
        FoodItem(name='Chicken Shawarma', tag='Shawarma', sub_tag='Wrap', price=7.00, image_file='shawarma.jpg', description='Middle Eastern grilled chicken wrapped in pita with garlic sauce and pickles.'),
        FoodItem(name='Beef Shawarma', tag='Shawarma', sub_tag='Wrap', price=8.50, image_file='shawarma1.jpg', description='Tender strips of marinated beef wrapped with tahini, onions, and parsley.'),
        FoodItem(name='Lamb Shawarma', tag='Shawarma', sub_tag='Wrap', price=9.00, image_file='shawarma2.jpg', description='Juicy, slow-roasted lamb slices wrapped in fresh khubz bread with veggies.'),
        FoodItem(name='Mixed Meat Shawarma', tag='Shawarma', sub_tag='Special', price=9.50, image_file='shawarma3.jpg', description='The best of both worlds: A mix of chicken and beef loaded with garlic mayo.'),
        FoodItem(name='Falafel Shawarma', tag='Shawarma', sub_tag='Veg', price=6.50, image_file='shawarma4.jpg', description='Crispy fried falafel balls wrapped with hummus, salad, and tahini sauce.'),
        FoodItem(name='Paneer Shawarma', tag='Shawarma', sub_tag='Veg', price=7.50, image_file='shawarma5.jpg', description='Grilled paneer cubes marinated in shawarma spices, wrapped with spicy mayo.'),
        FoodItem(name='Spicy Mexican Shawarma', tag='Shawarma', sub_tag='Spicy', price=8.00, image_file='shawarma6.jpg', description='A fusion wrap with jalapeños, hot salsa, and spicy chicken.'),
        FoodItem(name='Cheese Burst Shawarma', tag='Shawarma', sub_tag='Cheesy', price=8.99, image_file='shawarma7.jpg', description='Loaded with extra melted cheddar and mozzarella cheese for a gooey delight.'),
        FoodItem(name='Open Plate Shawarma', tag='Shawarma', sub_tag='Platter', price=11.00, image_file='shawarma8.jpg', description='Deconstructed shawarma served on a plate with fries, salad, and dip.'),
        FoodItem(name='Hummus & Shawarma', tag='Shawarma', sub_tag='Platter', price=10.50, image_file='shawarma9.jpg', description='A bowl of creamy hummus topped with savory grilled chicken shawarma meat.'),
        FoodItem(name='Turkish Doner', tag='Shawarma', sub_tag='Special', price=9.00, image_file='shawarma10.jpg', description='Traditional Turkish style meat served in thick bread with yogurt sauce.'),
        FoodItem(name='Jumbo Shawarma', tag='Shawarma', sub_tag='Large', price=12.00, image_file='shawarma11.jpg', description='Double the meat, double the size. A massive wrap for a massive appetite.'),

        # French Fries
        FoodItem(name='Classic Fries', tag='French Fries', sub_tag='Sides', price=4.50, image_file='french.jpg', description='Golden, salted shoestring french fries served hot and crispy.'),
        FoodItem(name='Peri Peri Fries', tag='French Fries', sub_tag='Spicy', price=5.50, image_file='french1.jpg', description='Crispy fries tossed in a spicy and tangy African bird’s eye chili seasoning.'),
        FoodItem(name='Cheesy Fries', tag='French Fries', sub_tag='Cheesy', price=6.50, image_file='french2.jpg', description='Smothered in a rich, gooey cheddar cheese sauce and melted mozzarella.'),
        FoodItem(name='Loaded Fries', tag='French Fries', sub_tag='Special', price=8.99, image_file='french3.jpg', description='The works: topped with bacon bits, cheese, sour cream, and jalapeños.'),
        FoodItem(name='Sweet Potato Fries', tag='French Fries', sub_tag='Healthy', price=6.00, image_file='french4.jpg', description='A sweeter, nutrient-rich alternative fried to a perfect caramelized crunch.'),
        FoodItem(name='Curly Fries', tag='French Fries', sub_tag='Fun', price=5.99, image_file='french5.jpg', description='Seasoned spiral-cut potatoes that are fun to eat and packed with flavor.'),
        FoodItem(name='Waffle Fries', tag='French Fries', sub_tag='Crispy', price=6.50, image_file='french6.jpg', description='Criss-cross cut potatoes with a larger surface area for maximum crunch.'),
        FoodItem(name='Cajun Fries', tag='French Fries', sub_tag='Spicy', price=5.50, image_file='french7.jpg', description='Dust with bold Southern spices like paprika, garlic, and cayenne pepper.'),
        FoodItem(name='Masala Fries', tag='French Fries', sub_tag='Desi', price=5.99, image_file='french8.jpg', description='Indian street-style fries tossed with chaat masala, chili powder, and lemon.'),
        FoodItem(name='Truffle Fries', tag='French Fries', sub_tag='Gourmet', price=9.50, image_file='french9.jpg', description='Luxurious fries drizzled with truffle oil and sprinkled with parmesan cheese.'),
        FoodItem(name='Chili Cheese Fries', tag='French Fries', sub_tag='Special', price=8.50, image_file='french10.jpg', description='Topped with a hearty scoop of spicy beef chili and shredded cheddar cheese.'),
        FoodItem(name='Potato Wedges', tag='French Fries', sub_tag='Thick', price=5.00, image_file='french11.jpg', description='Thick-cut potato wedges with the skin on, seasoned with herbs and garlic.'),

        # Popcorn
        FoodItem(name='Buttered Popcorn', tag='Popcorn', sub_tag='Snacks', price=3.00, image_file='popcorn.jpeg', description='Freshly popped corn tossed in rich, melted golden butter and sea salt.'),
        FoodItem(name='Caramel Popcorn', tag='Popcorn', sub_tag='Sweet', price=4.50, image_file='popcorn1.jpg', description='Crunchy popcorn coated in a sweet, sticky, and buttery caramel glaze.'),
        FoodItem(name='Cheese Popcorn', tag='Popcorn', sub_tag='Savory', price=4.00, image_file='popcorn2.jpg', description='Dusted generously with sharp cheddar cheese powder for a finger-licking treat.'),
        FoodItem(name='Spicy Masala Popcorn', tag='Popcorn', sub_tag='Spicy', price=3.50, image_file='popcorn3.jpg', description='Indian-style popcorn seasoned with turmeric, chili powder, and chaat masala.'),
        FoodItem(name='Chocolate Drizzle', tag='Popcorn', sub_tag='Dessert', price=5.00, image_file='popcorn4.jpg', description='Salty popcorn drizzled with melted dark and white chocolate.'),
        FoodItem(name='Tomato Chili Popcorn', tag='Popcorn', sub_tag='Spicy', price=3.99, image_file='popcorn5.jpg', description='Tangy tomato and spicy chili seasoning make this a zesty snack.'),
        FoodItem(name='Salt & Pepper', tag='Popcorn', sub_tag='Simple', price=3.00, image_file='popcorn6.jpg', description='Classic popcorn seasoned simply with sea salt and cracked black pepper.'),
        FoodItem(name='Peri Peri Popcorn', tag='Popcorn', sub_tag='Spicy', price=4.50, image_file='popcorn7.jpg', description='Bold and fiery African chili spices dusted over hot popcorn.'),
        FoodItem(name='BBQ Popcorn', tag='Popcorn', sub_tag='Savory', price=4.00, image_file='popcorn8.jpg', description='Smoky, sweet, and tangy barbecue seasoning coating every kernel.'),
        FoodItem(name='Rainbow Popcorn', tag='Popcorn', sub_tag='Kids', price=5.50, image_file='popcorn9.jpg', description='Sweet, colorful, fruit-flavored popcorn that is perfect for parties.'),
        FoodItem(name='Sour Cream & Onion', tag='Popcorn', sub_tag='Savory', price=4.25, image_file='popcorn10.jpg', description='The classic chip flavor, now on popcorn. Creamy, tangy, and oniony.'),
        FoodItem(name='Peanut Butter Popcorn', tag='Popcorn', sub_tag='Nutty', price=5.00, image_file='popcorn11.jpg', description='Coated in a sweet peanut butter glaze for a nutty, crunchy delight.'),

        # Chips (12 Items)
        FoodItem(name='Potato Chips', tag='Chips', sub_tag='Classic', price=2.50, image_file='potato.jpeg', description='Classic, crispy, and lightly salted potato chips. The perfect snack.'),
        FoodItem(name='BBQ Chips', tag='Chips', sub_tag='Savory', price=2.99, image_file='potato1.jpg', description='Smoky, sweet, and tangy barbecue seasoned chips with a satisfying crunch.'),
        FoodItem(name='Sour Cream & Onion', tag='Chips', sub_tag='Creamy', price=2.99, image_file='potato2.jpg', description='A fan favorite blend of tangy sour cream and zesty onion flavor.'),
        FoodItem(name='Salt & Vinegar', tag='Chips', sub_tag='Tangy', price=3.00, image_file='potato3.jpg', description='Bold and tangy vinegar flavor paired with sea salt for a mouth-puckering treat.'),
        FoodItem(name='Spicy Chili Chips', tag='Chips', sub_tag='Spicy', price=3.25, image_file='potato4.jpg', description='Red hot chili pepper seasoning for those who love a spicy kick.'),
        FoodItem(name='Tortilla Chips', tag='Chips', sub_tag='Corn', price=3.50, image_file='potato5.jpg', description='Authentic corn tortilla chips, perfect for dipping in salsa or guacamole.'),
        FoodItem(name='Cheesy Nachos', tag='Chips', sub_tag='Cheesy', price=4.50, image_file='potato6.jpg', description='Crispy tortilla chips smothered in rich nacho cheese dust.'),
        FoodItem(name='Banana Chips', tag='Chips', sub_tag='Sweet', price=3.99, image_file='potato7.jpg', description='Thinly sliced fried bananas, available in salted or sweet honey glazed options.'),
        FoodItem(name='Sweet Potato Chips', tag='Chips', sub_tag='Healthy', price=4.00, image_file='potato8.jpg', description='A healthier alternative made from sweet potatoes, offering a natural sweetness.'),
        FoodItem(name='Kettle Cooked', tag='Chips', sub_tag='Crunchy', price=3.50, image_file='potato9.jpg', description='Thicker cut and slow-cooked for an extra hard and satisfying crunch.'),
        FoodItem(name='Veggie Chips', tag='Chips', sub_tag='Healthy', price=4.50, image_file='potato10.jpg', description='A colorful mix of beetroot, carrot, and spinach chips.'),
        FoodItem(name='Jalapeño Chips', tag='Chips', sub_tag='Spicy', price=3.25, image_file='potato11.jpg', description='Zesty jalapeño heat balanced with a savory potato crunch.'),

        # Desserts
        FoodItem(name='Cheese Cake Slice', tag='Cheese Cake', price=6.50, image_file='cake.jpg', description='Creamy New York style cheesecake with a graham cracker crust.'),
        FoodItem(name='Gulab Jamun (4pc)', tag='Gulab Jamun', price=5.00, image_file='gulab.jpg', description='Soft milk-solid balls soaked in aromatic rose sugar syrup.'),
        FoodItem(name='Chocolate Donut', tag='Donut', price=2.50, image_file='donut.jpeg', description='Fluffy ring donut glazed with rich milk chocolate.'),
        FoodItem(name='Fudge Brownies', tag='Brownies', price=3.00, image_file='brownies.jpeg', description='Dense, fudgy chocolate brownies with a crackly top.'),
        FoodItem(name='Rice Pudding', tag='Puddings', price=4.00, image_file='pudding.jpeg', description='Creamy rice slow-cooked in milk with cardamom and nuts.'),
        FoodItem(name='Choco-Chip Cookies', tag='Cookies', price=2.00, image_file='cookies.jpeg', description='Chewy cookies loaded with semi-sweet chocolate chips.')
    ]
    db.session.add_all(menu_items)

    db.session.commit()
    flash('Database updated! All new items and descriptions added.', 'success')
    return redirect(url_for('home'))

@app.route('/fix_profile_pic')
def fix_profile_pic():
    if 'user' not in session: return "<h1>Please <a href='/login'>Login</a> first.</h1>"
    
    # 1. Get the current user
    user = User.query.filter_by(email=session['user']).first()
    
    # 2. Force the database to use 'default.jpg'
    user.image_file = 'default.jpg'
    db.session.commit()
    
    # 3. Check if the file actually exists on the computer
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'default.jpg')
    if os.path.exists(file_path):
        return "<h1>✅ SUCCESS! Database updated to 'default.jpg' and the file was found. <a href='/profile'>Go to Profile</a></h1>"
    else:
        return f"<h1>⚠️ Database updated, BUT... the file is missing from your folder!<br>Path checked: {file_path}</h1>"

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5003)