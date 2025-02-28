
from datetime import datetime, timedelta
from flask import Flask, json, render_template, request, redirect, send_from_directory, session, url_for, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Date, func
from werkzeug.utils import secure_filename
from flask_migrate import Migrate
import os

app = Flask(__name__)

app.secret_key = os.getenv('FLASK_SECRET_KEY', 'default_secret_key')

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///user_management.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)  # Initialize Flask-Migrate

# Define models
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(100), unique=True, nullable=False, default="admin")
    password = db.Column(db.String(100), nullable=False, default="admin123")

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    fullname = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    pincode = db.Column(db.String(6), nullable=False)

class Professional(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    fullname = db.Column(db.String(120), nullable=False)
    service_name = db.Column(db.String(120), nullable=False)
    experience = db.Column(db.Integer, nullable=False)
    document = db.Column(db.String(200), nullable=False)  # Stores the PDF path
    address = db.Column(db.String(200), nullable=False)
    pincode = db.Column(db.String(6), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Pending")  # New column for admin status
     # Relationships
    requests = db.relationship('ServiceRequest', back_populates='professional', cascade="all, delete")  # No cascade here
    
class Service(db.Model):
    __tablename__ = 'services'
    service_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    service_name = db.Column(db.String(100), nullable=False)
    base_price = db.Column(db.Float, nullable=False)
    time_required = db.Column(db.Integer, nullable=False)  # In hours or days
    description = db.Column(db.Text, nullable=True)

    # Relationships
    requests = db.relationship('ServiceRequest', back_populates='service')  # No cascade here


class ServiceRequest(db.Model):
    __tablename__ = 'service_requests'
    request_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    service_id = db.Column(db.Integer, db.ForeignKey('services.service_id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    professional_id = db.Column(db.Integer, db.ForeignKey('professional.id'), nullable=False)
    date_of_request = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    date_of_completion = db.Column(db.DateTime, nullable=True)  # Set by admin
    service_status = db.Column(
        db.Enum('Requested', 'In Progress', 'Completed', 'Closed', 'Rejected', name='service_status_enum'), 
        nullable=False, 
        default='Requested'
    )
    remark = db.Column(db.Text, nullable=True)

    # Relationships
    service = db.relationship('Service', back_populates='requests')
    feedback = db.relationship('Feedback', back_populates='service_request', uselist=False, cascade="all, delete")
    professional = db.relationship('Professional', back_populates='requests')    # No cascade here
    
class Feedback(db.Model):
    __tablename__ = 'feedback'
    feedback_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    request_id = db.Column(db.Integer, db.ForeignKey('service_requests.request_id'), nullable=False, unique=True)
    rating = db.Column(db.Integer, nullable=False)  # Ratings from 1 to 5
    remark = db.Column(db.Text, nullable=True)

    # Relationships
    service_request = db.relationship('ServiceRequest', back_populates='feedback')



default_admin_initialized = False
app.config['UPLOAD_FOLDER'] = 'uploads'  # Directory for PDF uploads
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/uploads/<filename>')
def serve_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.before_request
def add_default_admin():
    global default_admin_initialized
    if not default_admin_initialized:
        # Check if admin already exists in the database
        existing_admin = Admin.query.filter_by(user_id="admin").first()
        if not existing_admin:
            # Add default admin credentials
            default_admin = Admin(user_id="admin", password="admin123")
            db.session.add(default_admin)
            db.session.commit()
            print("Default admin created successfully.")
        else:
            print("Default admin already exists.")
        default_admin_initialized = True

@app.route('/')
def home():
    return render_template('index.html')



@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        user_id = request.form['user_id']
        password = request.form['password']
        
        # Verify admin credentials
        admin = Admin.query.filter_by(user_id=user_id, password=password).first()
        if admin:
            session['role'] = 'admin'  # Set the session role as 'admin'
            return redirect('/admin_dashboard')  # Redirect to admin dashboard
        else:
            flash('Invalid credentials', 'danger')

    return render_template('admin_login.html')

@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if 'role' in session and session['role'] == 'admin':
        if request.method == 'POST':
            # Add a new service
            service_name = request.form['service_name']
            base_price = request.form['base_price']
            time_required = request.form['time_required']
            description = request.form['description']

            # Save new service to the database
            new_service = Service(service_name=service_name, base_price=base_price, time_required=time_required, description=description)
            db.session.add(new_service)
            db.session.commit()
            flash('Service added successfully!', 'success')
            return redirect('/admin_dashboard')

        # Get all services for display in the dashboard
        services = Service.query.all()
        # Get all professionals for display in the dashboard
        professionals = Professional.query.all()
        
        return render_template('admin_dashboard.html', services=services, professionals=professionals)
    else:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))

    
# for deleting the service
@app.route('/delete_service/<int:service_id>', methods=['POST'])
def delete_service(service_id):
    if 'role' in session and session['role'] == 'admin':
        service = Service.query.get_or_404(service_id)
        db.session.delete(service)
        db.session.commit()
        flash('Service deleted successfully!', 'success')
        return redirect('/admin_dashboard')
    else:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))

#for editing the service
@app.route('/edit_service/<int:service_id>', methods=['GET', 'POST'])
def edit_service(service_id):
    if 'role' in session and session['role'] == 'admin':
        service = Service.query.get_or_404(service_id)

        if request.method == 'POST':
            service.service_name = request.form['service_name']
            service.base_price = request.form['base_price']
            service.time_required = request.form['time_required']
            service.description = request.form['description']
            db.session.commit()
            flash('Service updated successfully!', 'success')
            return redirect('/admin_dashboard')

        return render_template('edit_service.html', service=service)
    else:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))
# for approve professional
@app.route('/approve_professional/<int:professional_id>', methods=['POST'])
def approve_professional(professional_id):
    if 'role' in session and session['role'] == 'admin':
        professional = Professional.query.get_or_404(professional_id)
        professional.status = "Approved"
        db.session.commit()
        flash(f'Professional {professional.fullname} approved.', 'success')
        return redirect('/admin_dashboard')
    else:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))

#for reject professional
@app.route('/reject_professional/<int:professional_id>', methods=['POST'])
def reject_professional(professional_id):
    if 'role' in session and session['role'] == 'admin':
        professional = Professional.query.get_or_404(professional_id)
        professional.status = "Rejected"
        db.session.commit()
        flash(f'Professional {professional.fullname} rejected.', 'warning')
        return redirect('/admin_dashboard')
    else:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))

#for deleting prof
@app.route('/delete_professional/<int:professional_id>', methods=['POST'])
def delete_professional(professional_id):
    if 'role' in session and session['role'] == 'admin':
        professional = Professional.query.get_or_404(professional_id)
        db.session.delete(professional)
        db.session.commit()
        flash(f'Professional {professional.fullname} deleted.', 'danger')
        return redirect('/admin_dashboard')
    else:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('home'))



# Admin Search section
@app.route('/admin_search')
def admin_search():
    if 'role' in session and session['role'] == 'admin':
        return "<h1>Admin Search Section</h1>"  # Placeholder for search functionality
    else:
        return redirect(url_for('home'))
    
# Admin Summary section
@app.route('/admin_summary')
def admin_summary():
    if 'role' in session and session['role'] == 'admin':
        return "<h1>Admin Summary Section</h1>"  # Placeholder for summary content
    else:
        return redirect(url_for('home'))
    
# Logout functionality
@app.route('/logout')
def logout():
    session.clear()  # Clear session data
    return redirect(url_for('home'))  # Redirect to the index.html (home page)
    
@app.route('/customer_signup')
def customer_signup():
    return render_template('customer_signup.html')

@app.route('/register_customer', methods=['POST'])
def register_customer():
    fullname = request.form['name']
    email = request.form['email']
    password = request.form['password']
    address = request.form['address']
    pincode = request.form['pincode']

    new_customer = Customer(fullname=fullname, email=email, password=password, address=address, pincode=pincode)

    try:
        db.session.add(new_customer)
        db.session.commit()
        return redirect(url_for('home'))
    except Exception as e:
        return jsonify({"error": str(e)})
    
    
@app.route('/customer_dashboard', methods=['GET', 'POST'])
def customer_dashboard():
    if 'user_id' not in session or session.get('role') != 'Customer':
        return redirect('/login')  # Redirect to login if not authenticated
    
    # Fetch all available services
    services = Service.query.all()

    # Fetch the customer's service requests along with service name and professional name
    customer_requests = db.session.query(
        ServiceRequest,
        Service.service_name,
        Professional.fullname
    ).join(Service, ServiceRequest.service_id == Service.service_id) \
     .join(Professional, ServiceRequest.professional_id == Professional.id) \
     .filter(ServiceRequest.customer_id == session['user_id']) \
     .all()

    return render_template('customer_dashboard.html', services=services, customer_requests=customer_requests)

@app.route('/available_professionals/<service_name>', methods=['GET'])
def available_professionals(service_name):
    if 'user_id' not in session or session.get('role') != 'Customer':
        return redirect('/login')  # Redirect to login if not authenticated

    # Fetch the service and its professionals
    service = Service.query.filter_by(service_name=service_name).first()
    if not service:
        return "Service not found.", 404

    # Fetch only approved professionals offering the service
    professionals = Professional.query.filter(
        Professional.service_name == service_name,
        Professional.status == 'Approved'
    ).all()

    return render_template(
        'available_professionals.html',
        service=service,
        professionals=professionals
    )


@app.route('/create_service_request', methods=['POST'])
def create_service_request():
    if 'user_id' not in session or session.get('role') != 'Customer':
        return redirect('/login')  # Redirect to login if not authenticated

    # Extract form data
    service_id = request.form.get('service_id')
    professional_id = request.form.get('professional_id')
    customer_id = session['user_id']

    # Validate data
    if not service_id or not professional_id:
        return "Invalid request data.", 400
    
     # Fetch the service to get its time_required field
    service = Service.query.get(service_id)
    if not service:
        return "Service not found.", 404

    # Calculate the date of completion
    date_of_request = datetime.utcnow()
    date_of_completion = date_of_request + timedelta(days=service.time_required)

    # Create a new service request
    new_request = ServiceRequest(
        service_id=service_id,
        customer_id=customer_id,
        professional_id=professional_id,
        date_of_request=date_of_request,
        date_of_completion=date_of_completion,
        remark=service.description,
        service_status='Requested'
    )

    # Add to the database
    db.session.add(new_request)
    db.session.commit()

    return redirect('/customer_dashboard')  # Redirect to the dashboard after creation


@app.route('/close_service_request/<int:request_id>', methods=['POST', 'GET'])
def close_service_request(request_id):
    # Check if the customer is logged in
    if 'user_id' not in session or session.get('role') != 'Customer':
        return redirect('/login')

    # Get the specific service request
    service_request = ServiceRequest.query.get(request_id)
    if service_request is None or service_request.customer_id != session['user_id']:
        return "Request not found or unauthorized access.", 404

    # Mark the service request as 'Closed'
    service_request.service_status = 'Closed'
    service_request.date_of_completion = datetime.utcnow()
    db.session.commit()

    # Redirect to feedback form
    return redirect(url_for('submit_feedback', request_id=request_id))



@app.route('/submit_feedback/<int:request_id>', methods=['GET', 'POST'])
def submit_feedback(request_id):
    # Check if the customer is logged in
    if 'user_id' not in session or session.get('role') != 'Customer':
        return redirect('/login')

    # Get the specific service request
    service_request = ServiceRequest.query.get(request_id)
    if service_request is None or service_request.customer_id != session['user_id']:
        return "Request not found or unauthorized access.", 404

    # Fetch related service and professional details
    service = Service.query.get(service_request.service_id)
    professional = Professional.query.get(service_request.professional_id)

    # Expected and actual dates
    expected_date = service_request.date_of_request + timedelta(days=service.time_required)
    actual_date = service_request.date_of_completion

    if request.method == 'POST':
        # Save the feedback to the database
        rating = request.form['rating']
        remark = request.form['remark']

        feedback = Feedback(
            request_id=request_id,
            rating=rating,
            remark=remark
        )
        db.session.add(feedback)
        db.session.commit()

        # Redirect back to the dashboard
        return redirect('/customer_dashboard')

    # Render the feedback form
    return render_template('feedback_form.html', 
                           service_name=service.service_name, 
                           service_description=service.description,
                           professional_name=professional.fullname,
                           expected_date=expected_date.strftime('%Y-%m-%d'),
                           actual_date=actual_date.strftime('%Y-%m-%d'))


    
@app.route('/professional_signup')
def professional_signup():
    return render_template('professional_signup.html')
    

@app.route('/register_professional', methods=['POST'])
def register_professional():
    fullname = request.form['name']
    email = request.form['email']
    password = request.form['password']
    service_name = request.form['service_name']
    experience = request.form['experience']
    address = request.form['address']
    pincode = request.form['pincode']

    # Handle file upload
    document = request.files['document']
    document_path = os.path.join(app.config['UPLOAD_FOLDER'], document.filename)
    document.save(document_path)

    new_professional = Professional(
        fullname=fullname, 
        email=email, 
        password=password, 
        service_name=service_name, 
        experience=experience, 
        document=document.filename, 
        address=address, 
        pincode=pincode
    )

    try:
        db.session.add(new_professional)
        db.session.commit()
        return redirect(url_for('home'))
    except Exception as e:
        return jsonify({"error": str(e)})
    
@app.route('/professional_dashboard', methods=['GET'])
def professional_dashboard():
    # Assuming you have a current_professional variable holding the logged-in professional's ID
   

    professional_id = session.get('user_id')  # Assuming the professional's ID is stored in the session
    today = datetime.utcnow().date() # Get current date

    # Fetch today's requests for the logged-in professional
    today_requests = (
        db.session.query(ServiceRequest, Customer.fullname, Customer.address, Customer.pincode)
        .join(Customer, ServiceRequest.customer_id == Customer.id)
        .filter(
            ServiceRequest.professional_id == professional_id,
            func.date(ServiceRequest.date_of_request) == today,
        )
        .all()
    )
     # Fetch closed services
    closed_services = get_closed_services(professional_id)

    return render_template(
        'professional_dashboard.html',
        today_requests=today_requests,
        closed_services=closed_services
    )

def get_closed_services(professional_id):
    # Query for closed services related to the professional
    closed_services = (
        db.session.query(
            ServiceRequest.service_id,
            Customer.fullname.label("customer_name"),
            Customer.address,
            Customer.pincode,
            ServiceRequest.date_of_completion,
            func.coalesce(Feedback.rating, "Not Rated Yet").label("rating")
        )
        .join(Customer, ServiceRequest.customer_id == Customer.id)
        .outerjoin(Feedback, ServiceRequest.request_id == Feedback.request_id)
        .filter(
            ServiceRequest.professional_id == professional_id,
            ServiceRequest.service_status == "Closed"
        )
        .all()
    )
    return closed_services
    


@app.route('/accept_request/<int:request_id>', methods=['POST'])
def accept_request(request_id):
    request_entry = ServiceRequest.query.get(request_id)
    if request_entry and request_entry.service_status == 'Requested':
        request_entry.service_status = 'In Progress'
        db.session.commit()
    return redirect(url_for('professional_dashboard'))

@app.route('/reject_request/<int:request_id>', methods=['POST'])
def reject_request(request_id):
    request_entry = ServiceRequest.query.get(request_id)
    if request_entry and request_entry.service_status == 'Requested':
        request_entry.service_status = 'Rejected'
        db.session.commit()
    return redirect(url_for('professional_dashboard'))

@app.route('/professional_summary', methods=['GET'])
def professional_summary():
    # Get logged-in professional ID
    if 'user_id' not in session or session.get('role') != 'Professional':
        return redirect('/login')

    professional_id = session.get('user_id')

    # Fetch counts of service statuses
    service_status_counts = db.session.query(
        ServiceRequest.service_status,
        func.count(ServiceRequest.request_id).label('count')
    ).filter_by(professional_id=professional_id) \
     .group_by(ServiceRequest.service_status) \
     .all()

    # Prepare data for histogram (status and counts)
    histogram_data = {
        'statuses': [status[0] for status in service_status_counts],
        'counts': [status[1] for status in service_status_counts]
    }

    # Fetch feedback ratings for the professional's services
    feedback_counts = db.session.query(
        Feedback.rating,
        func.count(Feedback.feedback_id).label('count')
    ).join(ServiceRequest, Feedback.request_id == ServiceRequest.request_id) \
     .filter(ServiceRequest.professional_id == professional_id) \
     .group_by(Feedback.rating) \
     .all()

    # Prepare data for pie chart (ratings and counts)
    piechart_data = {
        'ratings': [str(rating[0]) if rating[0] else "Not Rated" for rating in feedback_counts],
        'counts': [rating[1] for rating in feedback_counts]
    }

    # Convert data to JSON for Chart.js
    histogram_data_json = json.dumps(histogram_data)
    piechart_data_json = json.dumps(piechart_data)

    return render_template(
        'professional_summary.html',
        histogram_data=histogram_data_json,
        piechart_data=piechart_data_json
    )


@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']
    role = request.form['role']

    if role == 'Customer':
        user = Customer.query.filter_by(email=email, password=password).first()
    elif role == 'Professional':
        user = Professional.query.filter_by(email=email, password=password).first()
    else:
        return "Invalid role selected.", 400

    if user:
        session['user_id'] = user.id  # Store user ID in session
        session['role'] = role  # Store role in session
        if role == 'Customer':
            return redirect('/customer_dashboard')
        elif role == 'Professional':
            return redirect('/professional_dashboard')
    else:
        return "Invalid credentials. Please try again."

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
