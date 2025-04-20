from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
import boto3
from datetime import datetime, timedelta
from functools import wraps
import jwt as pyjwt

app = Flask(__name__, static_folder='static')
CORS(app, supports_credentials=True)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///bookstore.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-jwt-secret-key')
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/uploads')

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# AWS S3 configuration
s3 = boto3.client('s3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)
BUCKET_NAME = os.getenv('S3_BUCKET_NAME')

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

# Serve static files
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    books = db.relationship('Book', backref='owner', lazy=True)

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        
        if auth_header:
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            data = pyjwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.get(data['user_id'])
            if not current_user:
                return jsonify({'error': 'User not found'}), 401
        except Exception as e:
            return jsonify({'error': f'Token is invalid: {str(e)}'}), 401
            
        return f(current_user, *args, **kwargs)
    return decorated

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Username and password are required'}), 400
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 400
    
    hashed_password = generate_password_hash(data['password'])
    
    user = User(
        username=data['username'],
        password_hash=hashed_password
    )
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({'message': 'User created successfully'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Username and password are required'}), 400
    
    user = User.query.filter_by(username=data['username']).first()
    
    if not user or not check_password_hash(user.password_hash, data['password']):
        return jsonify({'error': 'Invalid username or password'}), 401
    
    # Generate token using PyJWT
    token = pyjwt.encode({
        'user_id': user.id,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }, app.config['JWT_SECRET_KEY'])
    
    return jsonify({
        'message': 'Login successful',
        'token': token,
        'user_id': user.id,
        'username': user.username
    }), 200

@app.route('/logout', methods=['POST'])
@token_required
def logout(current_user):
    return jsonify({'message': 'Logged out successfully'}), 200

@app.route('/books', methods=['GET'])
def get_books():
    books = Book.query.all()
    return jsonify([{
        'id': book.id,
        'title': book.title,
        'price': book.price,
        'image_url': book.image_url,
        'user_id': book.user_id
    } for book in books]), 200

@app.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    book = Book.query.get_or_404(book_id)
    return jsonify({
        'id': book.id,
        'title': book.title,
        'price': book.price,
        'image_url': book.image_url,
        'user_id': book.user_id
    }), 200

@app.route('/books', methods=['POST'])
@token_required
def add_book(current_user):
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    
    file = request.files['image']
    title = request.form.get('title')
    price = request.form.get('price')
    
    if not title or not price:
        return jsonify({'error': 'Title and price are required'}), 400
    
    try:
        price = float(price)
    except ValueError:
        return jsonify({'error': 'Price must be a number'}), 400
    
    # Generate a unique filename
    filename = f"{datetime.now().timestamp()}_{file.filename}"
    
    # If using S3
    if os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY') and BUCKET_NAME:
        try:
            s3.upload_fileobj(file, BUCKET_NAME, filename)
            image_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{filename}"
        except Exception as e:
            return jsonify({'error': f'Failed to upload image: {str(e)}'}), 500
    else:
        # Local file storage
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        image_url = f"http://localhost:5000/static/uploads/{filename}"
    
    book = Book(
        title=title,
        price=price,
        image_url=image_url,
        user_id=current_user.id
    )
    db.session.add(book)
    db.session.commit()
    
    return jsonify({
        'id': book.id,
        'title': book.title,
        'price': book.price,
        'image_url': book.image_url
    }), 201

@app.route('/books/<int:book_id>', methods=['PUT'])
@token_required
def update_book(current_user, book_id):
    book = Book.query.get_or_404(book_id)
    
    # Check if the current user owns the book
    if book.user_id != current_user.id:
        return jsonify({'error': 'You do not have permission to edit this book'}), 403
    
    # Update book details
    title = request.form.get('title')
    price = request.form.get('price')
    
    if title:
        book.title = title
    
    if price:
        try:
            book.price = float(price)
        except ValueError:
            return jsonify({'error': 'Price must be a number'}), 400
    
    # Update image if provided
    if 'image' in request.files:
        file = request.files['image']
        if file and file.filename:
            # Generate a unique filename
            filename = f"{datetime.now().timestamp()}_{file.filename}"
            
            # If using S3
            if os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY') and BUCKET_NAME:
                try:
                    s3.upload_fileobj(file, BUCKET_NAME, filename)
                    image_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{filename}"
                except Exception as e:
                    return jsonify({'error': f'Failed to upload image: {str(e)}'}), 500
            else:
                # Local file storage
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                image_url = f"http://localhost:5000/static/uploads/{filename}"
            
            # Update image URL
            book.image_url = image_url
    
    db.session.commit()
    
    return jsonify({
        'id': book.id,
        'title': book.title,
        'price': book.price,
        'image_url': book.image_url
    }), 200

@app.route('/books/<int:book_id>', methods=['DELETE'])
@token_required
def delete_book(current_user, book_id):
    book = Book.query.get_or_404(book_id)
    
    # Check if the current user owns the book
    if book.user_id != current_user.id:
        return jsonify({'error': 'You do not have permission to delete this book'}), 403
    
    db.session.delete(book)
    db.session.commit()
    
    return jsonify({'message': 'Book deleted successfully'}), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Create a test user if none exists
        if not User.query.filter_by(username='test').first():
            test_user = User(
                username='test',
                password_hash=generate_password_hash('password')
            )
            db.session.add(test_user)
            db.session.commit()
            print("Created test user: username='test', password='password'")
    
    app.run(debug=True) 