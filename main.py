from io import BytesIO,StringIO
import os
from flask import Flask, flash, render_template, request,redirect, send_file,send_from_directory,make_response,session,current_app
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
from flask_bcrypt import Bcrypt
import pdfkit
import razorpay
from fpdf import FPDF

app=Flask(__name__)
app.config["SECRET_KEY"]='65b0b774279de460f1cc5c92'
app.config['SQLALCHEMY_DATABASE_URI']="sqlite:///ums.sqlite"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False
app.config["SESSION_PERMANENT"]=False
app.config["SESSION_TYPE"]='filesystem'
db=SQLAlchemy(app)
bcrypt=Bcrypt(app)
Session(app)


#Upload Class
class Upload(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    userid=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False)
    ccertname=db.Column(db.String(50), nullable=False)
    pcertname=db.Column(db.String(50), nullable=False)
    ccertificate=db.Column(db.LargeBinary)
    pcertificate=db.Column(db.LargeBinary)

    def __repr__(self):
        return f'Upload("{self.pcertname}","{self.ccertname}","{self.ccertificate}","{self.pcertificate}","{self.userid}")'

# User Class
class User(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    fname=db.Column(db.String(255), nullable=False)
    lname=db.Column(db.String(255), nullable=False)
    email=db.Column(db.String(255), nullable=False)
    username=db.Column(db.String(255), nullable=False)
    phone=db.Column(db.String(255), nullable=False)
    password=db.Column(db.String(255), nullable=False)
    status=db.Column(db.Integer,default=-1, nullable=False)
    paystatus=db.Column(db.Integer,default=0, nullable=False)
    uploads=db.relationship("Upload", backref="User",primaryjoin='User.id==Upload.userid',lazy='dynamic')

    def __repr__(self):
        return f'User("{self.id}","{self.fname}","{self.lname}","{self.email}","{self.phone}","{self.username}","{self.status}","{self.paystatus}")'

# create admin Class
class Admin(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    username=db.Column(db.String(255), nullable=False)
    password=db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f'Admin("{self.username}","{self.id}")'

# create table
with app.app_context():
    #admin=Admin(username='San1976',password=bcrypt.generate_password_hash('San1976@',10))
    #db.session.add(admin)
    #db.session.commit()
    db.create_all()

# insert admin data one time only one time insert this data
# latter will check the condition


# main index 
@app.route('/')
def index():
    return render_template('index.html',title="")


# admin loign
@app.route('/admin/',methods=["POST","GET"])
def adminIndex():
    # chect the request is post or not
    if request.method == 'POST':
        # get the value of field
        username = request.form.get('username')
        password = request.form.get('password')
        # check the value is not empty
        if username=="" and password=="":
            flash('Please fill all the field','danger')
            return redirect('/admin/')
        else:
            # login admin by username 
            admins=Admin().query.filter_by(username=username).first()
            if admins and bcrypt.check_password_hash(admins.password,password):
                session['admin_id']=admins.id
                session['admin_name']=admins.username
                flash('Login Successfully','success')
                return redirect('/admin/dashboard')
            else:
                flash('Invalid Email and Password','danger')
                return redirect('/admin/')
    else:
        return render_template('admin/index.html',title="Admin Login")

# admin Dashboard
@app.route('/admin/dashboard')
def adminDashboard():
    if not session.get('admin_id'):
        return redirect('/admin/')
    totalUser=User.query.count()
    totalApprove=User.query.filter_by(status=1).count()
    totalNotApprove=User.query.filter_by(status=-1).count()
    return render_template('admin/dashboard.html',title="Admin Dashboard",totalUser=totalUser,totalApprove=totalApprove,NotTotalApprove=totalNotApprove)

# admin get all user 
@app.route('/admin/get-all-user', methods=["POST","GET"])
def adminGetAllUser():
    if not session.get('admin_id'):
        return redirect('/admin/')
    if request.method== "POST":
        search=request.form.get('search')
        users=User.query.filter(User.username.like('%'+search+'%')).all()
        uploads=Upload.query.filter(Upload.id.like('%'+search+'%')).all()
        return render_template('admin/all-user.html',title='Approve User',users=users)
    else:
        users=User.query.all()
        return render_template('admin/all-user.html',title='Approve User',users=users)

# dowload documents
@app.route('/admin/downloadpc/<int:id>')
def admindownloadpc(id):
    if not session.get('admin_id'):
        return redirect('/admin/')
    docs=Upload.query.filter_by(id=id).first()
    flash('Downloaded Successfully','success')
    name=docs.pcertname
    return send_file(BytesIO(docs.pcertificate),mimetype="text/pdf",download_name=name,as_attachment=True)

@app.route('/admin/downloadcc/<int:id>')
def admindownloadcc(id):
    if not session.get('admin_id'):
        return redirect('/admin/')
    docs=Upload.query.filter_by(id=id).first()
    flash('Downloaded Successfully','success')
    name=docs.ccertname
    return send_file(BytesIO(docs.ccertificate),mimetype="text/pdf",download_name=name,as_attachment=True)

@app.route('/admin/approve-user/<int:id>')
def adminApprove(id):
    if not session.get('admin_id'):
        return redirect('/admin/')
    User().query.filter_by(id=id).update(dict(status=1))
    db.session.commit()
    flash('Approve Successfully','success')
    return redirect('/admin/get-all-user')

@app.route('/admin/disapprove-user/<int:id>')
def admindisApprove(id):
    if not session.get('admin_id'):
        return redirect('/admin/')
    User().query.filter_by(id=id).update(dict(status=0))
    db.session.commit()
    flash('DisApprove Successfully','success')
    return redirect('/admin/get-all-user')

# change admin password
@app.route('/admin/change-admin-password',methods=["POST","GET"])
def adminChangePassword():
    admin=Admin.query.get(1)
    if request.method == 'POST':
        username=request.form.get('username')
        password=request.form.get('password')
        if username == "" or password=="":
            flash('Please fill the field','danger')
            return redirect('/admin/change-admin-password')
        else:
            Admin().query.filter_by(username=username).update(dict(password=bcrypt.generate_password_hash(password,10)))
            db.session.commit()
            flash('Admin Password update successfully','success')
            return redirect('/admin/change-admin-password')
    else:
        return render_template('admin/admin-change-password.html',title='Admin Change Password',admin=admin)

# admin logout
@app.route('/admin/logout')
def adminLogout():
    if not session.get('admin_id'):
        return redirect('/admin/')
    if session.get('admin_id'):
        session['admin_id']=None
        session['admin_name']=None
        return redirect('/')
# -------------------------user area----------------------------


# User login
@app.route('/user/',methods=["POST","GET"])
def userIndex():
    if  session.get('user_id'):
        return redirect('/user/dashboard')
    if request.method=="POST":
        # get the name of the field
        email=request.form.get('email')
        password=request.form.get('password')
        # check user exist in this email or not
        users=User().query.filter_by(email=email).first()
        if users and bcrypt.check_password_hash(users.password,password):
            session['user_id']=users.id
            session['username']=users.username
            return redirect('/user/dashboard')
        else:
            flash('Invalid Email and Password','danger')
            return redirect('/user/')
    else:
        return render_template('user/index.html',title="User Login")

# User Register
@app.route('/user/signup',methods=['POST','GET'])
def userSignup():
    if  session.get('user_id'):
        return redirect('/user/dashboard')
    if request.method=='POST':
        # get all input field name
        fname=request.form.get('fname')
        lname=request.form.get('lname')
        email=request.form.get('email')
        username=request.form.get('username')
        phone=request.form.get('phone')
        password=request.form.get('password')
        # check all the field is filled are not
        if fname =="" or lname=="" or email=="" or password=="" or username=="" or phone=="":
            flash('Please fill all the field','danger')
            return redirect('/user/signup')
        else:
            is_email=User().query.filter_by(email=email).first()
            if is_email:
                flash('Email already Exist','danger')
                return redirect('/user/signup')
            else:
                hash_password=bcrypt.generate_password_hash(password,10)
                user=User(fname=fname,lname=lname,email=email,password=hash_password,phone=phone,username=username)
                db.session.add(user)
                db.session.commit()
                flash('Account Created Successfully','success')
                return redirect('/user/')
    else:
        return render_template('user/signup.html',title="User Signup")


# user dashboard
@app.route('/user/dashboard')
def userDashboard():
    if not session.get('user_id'):
        return redirect('/user/')
    if session.get('user_id'):
        id=session.get('user_id')
        users=User().query.filter_by(id=id).first()
        return render_template('user/dashboard.html',title="User Dashboard",users=users)

# user challan Payment
@app.route('/user/paytc/<id>',methods=['POST','GET'])
def userpayment(id):
    if not session.get('user_id'):
        return redirect('/user/')
    if session.get('user_id'):
        id=session.get('user_id')
        client = razorpay.Client(auth=("rzp_test_rkhhrxjoQABOoR", "FH6z5T7XZ6TDVq1Q4zfQJGFx"))
        payment=client.order.create({'amount':int(100*100),'currency':'INR','payment_capture':'1'})
        client.set_app_details({"title" : "Online TC Form Builder ", "version" : "1.0"})
        return render_template('navbar.html',title="Payment Gateway",payment=payment)

# user Submit documents for tcform
@app.route('/user/uploaddoc',methods=['POST','GET'])
def uploaddoc():
    if not session.get('user_id'):
        return redirect('/user/')

    if session.get('user_id'):
        uid=session.get('user_id')
        usersid=Upload().query.filter_by(userid=uid).first()
        appstatus=User().query.filter_by(id=uid).first()
        if usersid and appstatus.status== 1 :
            flash('Documents are approved by Admin','danger')
            return redirect('/user/dashboard')

        elif usersid and appstatus.status==2 :
            flash('Documents are Already submitted , Please wait Admin will approve your documents in 20-30 min','danger')
            return redirect('/user/dashboard')

        elif request.method=="POST":
            if usersid and appstatus.status==0:
                file1=request.files['file1']
                file2=request.files['file2']
                flash('Documents you have uploaded are not approved by Admin, Please recheck your documents and upload again !','danger')
                upload=Upload().query.filter_by(userid=uid).update(dict(ccertname=file2.filename,pcertname=file1.filename,pcertificate=file1.read(),ccertificate=file2.read(),userid=uid))
                db.session.commit()
                return redirect('/user/dashboard')
            else:
                file1=request.files['file1']
                file2=request.files['file2']
                upload=Upload(ccertname=file2.filename,pcertname=file1.filename,pcertificate=file1.read(),ccertificate=file2.read(),userid=uid)
                user=User().query.filter_by(id=uid).update(dict(status=2))
                db.session.add(upload,user)
                db.session.commit()
                flash('Documents are submitted , Please wait Admin will approve your documents in 20-30 min','danger')
                return redirect('/user/dashboard')

        else:
            flash('Please upload documents','danger')
            return render_template('/user/uploaddoc.html',title="Upload Documents")

# user tcform 
@app.route('/user/tcform',methods=['POST','GET'])
def usertcform():
    if  not session.get('user_id'):
        return redirect('/user')

    if session.get('user_id'):
        id=session.get('user_id')
        users=User().query.filter_by(id=id).first()
        if users:
            # check the admin approve your account are not
            is_approve=User.query.filter_by(id=users.id).first()
            # first return the is_approve:
            if is_approve.status == 2 or is_approve.status == -1 or is_approve.status == 0:
                flash('Your submitted documents are not yet approved by Admin','danger')
                return redirect('/user/dashboard')
            else:
                if request.method=='POST':
                    # get all input field name
                    name=request.form.get('name')
                    gender=request.form.get('gender')
                    fname=request.form.get('fname')
                    mname=request.form.get('mname')
                    dob=request.form.get('dob')
                    nation=request.form.get('nation')
                    caste=request.form.get('caste')
                    doa=request.form.get('doa')
                    course=request.form.get('course')
                    afrom=request.form.get('afrom')
                    ato=request.form.get('ato')
                    qualified=request.form.get('qualified')
                    dues=request.form.get('dues')
                    conduct=request.form.get('conduct')
                    dissue=request.form.get('dissue')
                    reason=request.form.get('reason')
                    remarks=request.form.get('remarks')
                    # check all the field is filled are not
                    if name=="" or fname =="" or gender =="" or mname=="" or nation=="" or caste=="" or doa=="" or course=="" or dob=="" or afrom=="" or ato=="" or qualified=="" or dues=="" or conduct=="" or dissue=="" or reason=="" or remarks=="":
                        flash('Please fill all the field','danger')
                        return redirect('/user/tcform')
                    else:
                        flash('TC Form Submitted Successfully , Please download your TC ','success')
                        pdf = FPDF()
                        pdf.add_page()
                        pdf.set_font("Arial", size = 15)
                        pdf.cell(0, 10, txt = "TRANSFER CERTIFICATE",ln = 2, align = 'C')
                        pdf.cell(0, 0, txt = "---------------------------------------",ln = 2, align = 'C')
                        pdf.cell(0, 10,ln=2)
                        pdf.cell(0, 10, txt = "Student Name                                                                    : "+name,ln = 2, align = 'L')
                        pdf.cell(0, 10, txt = "Gender                                                                               : "+gender,ln = 2, align = 'L')
                        pdf.cell(0, 10, txt = "Father's Name                                                                   : "+fname,ln = 2, align = 'L')
                        pdf.cell(0, 10, txt = "Mother's Name                                                                  : "+mname,ln = 2, align = 'L')
                        pdf.cell(0, 10, txt = "Date Of Birth ( DD/MM/YYYY)                                          : " + dob,ln = 2, align = 'L')
                        pdf.cell(0, 10, txt = "Nationality                                                                         : " + nation,ln = 2, align = 'L')
                        pdf.cell(0, 10, txt = "Whether the Candidate belongs to S.C/S.T/O.B.C           : " + caste,ln = 2, align = 'L')
                        pdf.cell(0, 10, txt = "Date of Admission                                                             : " + doa,ln = 2, align = 'L')
                        pdf.cell(0, 10, txt = "Class/Course Enrolled In                                                  : " + course,ln = 2, align = 'L')
                        pdf.cell(0, 10, txt = "Academic Year From                                                        : " + afrom,ln = 2, align = 'L')
                        pdf.cell(0, 10, txt = "Academic Year To                                                            : " + ato,ln = 2, align = 'L')
                        pdf.cell(0, 10, txt = "Whether Qualified for promotion to higher studies           : " + qualified,ln = 2, align = 'L')
                        pdf.cell(0, 10, txt = "Whether the Student has paid all dues to the Institution  : " + dues,ln = 2, align = 'L')
                        pdf.cell(0, 10, txt = "General Conduct                                                              : " + conduct,ln = 2, align = 'L')
                        pdf.cell(0, 10, txt = "Date Of issue of Certificate( DD/MM/YYYY)                    : " + dissue,ln = 2, align = 'L')
                        pdf.cell(0, 10, txt = "Reason for leaving the College                                        : " + reason,ln = 2, align = 'L')
                        pdf.cell(0, 10, txt = "Any Remarks                                                                    : " + remarks,ln = 2, align = 'L')
                        
                        pdf.cell(0, 70, txt = "Principal Signature                                                      Administration Stamp",ln = 2, align = 'L')
                        
                         
                        # save the pdf with name .pdf
                        filename=name+".pdf"

                        pdf.output(filename)
                        path=os.getcwd()+"/"

                        return send_from_directory(path,filename)
                        #return redirect('/user/dashboard')
                else:
                    return render_template('/user/tcform.html',title="TC Form")

# user logout
@app.route('/user/logout')
def userLogout():
    if not session.get('user_id'):
        return redirect('/user/')

    if session.get('user_id'):
        session['user_id'] = None
        session['username'] = None
        return redirect('/user/')

@app.route('/user/change-password',methods=["POST","GET"])
def userChangePassword():
    if not session.get('user_id'):
        return redirect('/user/')
    if request.method == 'POST':
        email=request.form.get('email')
        password=request.form.get('password')
        if email == "" or password == "":
            flash('Please fill the field','danger')
            return redirect('/user/change-password')
        else:
            users=User.query.filter_by(email=email).first()
            if users:
               hash_password=bcrypt.generate_password_hash(password,10)
               User.query.filter_by(email=email).update(dict(password=hash_password))
               db.session.commit()
               flash('Password Change Successfully','success')
               return redirect('/user/change-password')
            else:
                flash('Invalid Email','danger')
                return redirect('/user/change-password')

    else:
        return render_template('user/change-password.html',title="Change Password")

# user update profile
@app.route('/user/update-profile', methods=["POST","GET"])
def userUpdateProfile():
    if not session.get('user_id'):
        return redirect('/user/')
    if session.get('user_id'):
        id=session.get('user_id')
    users=User.query.get(id)
    if request.method == 'POST':
        # get all input field name
        fname=request.form.get('fname')
        lname=request.form.get('lname')
        email=request.form.get('email')
        username=request.form.get('username')
        phone=request.form.get('phone')
        if fname =="" or lname=="" or email=="" or username=="" or phone=="":
            flash('Please fill all the field','danger')
            return redirect('/user/update-profile')
        else:
            session['username']=None
            User.query.filter_by(id=id).update(dict(fname=fname,lname=lname,email=email,phone=phone,username=username))
            db.session.commit()
            session['username']=username
            flash('Profile update Successfully','success')
            return redirect('/user/dashboard')
    else:
        return render_template('user/update-profile.html',title="Update Profile",users=users)


if __name__=="__main__":
    app.run(debug=True)