from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'your_secure_secret_key_here'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# MongoDB setup
client = MongoClient('mongodb://localhost:27017/')
db = client.image_catalog

# Helper function
def get_user_images():
    return list(db.images.find({'user_id': session['user_id']}).sort('upload_date', -1))

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect('/my-images')
    images = list(db.images.find().sort('upload_date', -1).limit(20))
    return render_template('index.html', images=images)

@app.route('/my-images')
def my_images():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('my_images.html', images=get_user_images())

@app.route('/image/<image_id>')
def image_detail(image_id):
    try:
        image = db.images.find_one({'_id': ObjectId(image_id)})
        if image:
            image['formatted_date'] = image['upload_date'].strftime("%Y-%m-%d %H:%M:%S")
            return render_template('image_detail.html', image=image)
        flash('Image not found')
        return redirect('/')
    except:
        flash('Invalid image ID')
        return redirect('/')

@app.route('/insert', methods=['GET', 'POST'])
def insert():
    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        try:
            files = request.files.getlist('image')
            if not files or all(file.filename == '' for file in files):
                flash('No files selected')
                return redirect('/insert')
            
            image_data_list = []
            for file in files:
                if file.filename == '':
                    continue
                
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                image_data = {
                    'name': request.form['name'],
                    'description': request.form['description'],
                    'filename': filename,
                    'upload_date': datetime.utcnow(),
                    'user_id': session['user_id'],
                    'contact_name': request.form['contact_name'],
                    'contact_email': request.form['contact_email'],
                    'contact_phone': request.form['contact_phone']
                }
                image_data_list.append(image_data)
            
            db.images.insert_many(image_data_list)
            flash('Images uploaded successfully!')
            return redirect('/my-images')
        except Exception as e:
            flash(f'Error: {str(e)}')
    return render_template('insert.html')

@app.route('/edit-image/<image_id>', methods=['GET', 'POST'])
def edit_image(image_id):
    if 'user_id' not in session:
        return redirect('/login')

    try:
        image = db.images.find_one({
            '_id': ObjectId(image_id),
            'user_id': session['user_id']
        })
        
        if not image:
            flash('Image not found or unauthorized')
            return redirect('/my-images')

        if request.method == 'POST':
            update_data = {
                'name': request.form['name'],
                'description': request.form['description'],
                'upload_date': datetime.utcnow(),
                'contact_name': request.form['contact_name'],
                'contact_email': request.form['contact_email'],
                'contact_phone': request.form['contact_phone']
            }

            # Handle file update
            if 'image' in request.files:
                file = request.files['image']
                if file.filename != '':
                    # Remove old file
                    old_file = os.path.join(app.config['UPLOAD_FOLDER'], image['filename'])
                    if os.path.exists(old_file):
                        os.remove(old_file)
                    
                    # Save new file
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    update_data['filename'] = filename

            db.images.update_one(
                {'_id': ObjectId(image_id)},
                {'$set': update_data}
            )
            flash('Image updated successfully!')
            return redirect('/my-images')

        return render_template('insert.html', image=image)

    except Exception as e:
        flash(f'Error: {str(e)}')
        return redirect('/my-images')

@app.route('/delete-image/<image_id>')
def delete_image(image_id):
    if 'user_id' not in session:
        return redirect('/login')

    try:
        image = db.images.find_one({
            '_id': ObjectId(image_id),
            'user_id': session['user_id']
        })

        if image:
            # Remove file
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], image['filename'])
            if os.path.exists(file_path):
                os.remove(file_path)
            
            db.images.delete_one({'_id': ObjectId(image_id)})
            flash('Image deleted successfully')
        else:
            flash('Image not found or unauthorized')

    except Exception as e:
        flash(f'Error deleting image: {str(e)}')

    return redirect('/my-images')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect('/my-images')

    if request.method == 'POST':
        user = db.users.find_one({'email': request.form['email']})
        if user and user['password'] == request.form['password']:
            session['user_id'] = str(user['_id'])
            return redirect('/my-images')
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user_id' in session:
        return redirect('/my-images')

    if request.method == 'POST':
        if db.users.find_one({'email': request.form['email']}):
            flash('Email already exists')
            return redirect('/signup')
        
        user = {
            'email': request.form['email'],
            'password': request.form['password'],
            'created_at': datetime.utcnow()
        }
        db.users.insert_one(user)
        session['user_id'] = str(user['_id'])
        return redirect('/my-images')
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect('/')

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)