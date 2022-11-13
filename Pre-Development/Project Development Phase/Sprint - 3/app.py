from flask import Flask, render_template, flash, redirect, url_for, session, request
from wtforms import Form, StringField, TextAreaField, PasswordField, validators, SelectField, IntegerField
from passlib.hash import sha256_crypt
from functools import wraps
import ibm_db
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase

app = Flask(__name__)
app.secret_key = 'a'

conn=ibm_db.connect("DATABASE=bludb;HOSTNAME=cfd8-47b7-4937-840d-d791d0218660.bs2io90l08kqb1od8lcg.databases.appdomain.cloud;PORT=31864;SECURITY=SSL;SSLServerCertificate=DigiCertGlobalRootCA.crt;UID=bsp63741;PWD=WFserEZz6UKSVeHR;",'','')

print("Hello")


@app.route('/')
def index():
    return render_template('home.html')

@app.route('/products')
def products():

    sql = "SELECT * FROM PRODUCTS"
    stmt = ibm_db.prepare(conn,sql)
    ibm_db.execute(stmt)
    res = ibm_db.fetch_assoc(stmt)

    # print(res)
    result= []

    while(res):
        result.append(res["PRODUCT_ID"])
        res = ibm_db.fetch_assoc(stmt)

    # print(result)

    if result:
        return render_template('products.html', products = result)
    else:
        msg='No products found'
        return render_template('products.html', msg=msg)


@app.route('/locations')
def locations():

    sql = "SELECT * FROM LOCATIONS"
    stmt = ibm_db.prepare(conn,sql)
    ibm_db.execute(stmt)
    res = ibm_db.fetch_assoc(stmt)

    # print(res)
    locations= []

    while(res):
        locations.append(res["LOCATION_ID"])
        res = ibm_db.fetch_assoc(stmt)

    # print(locations)

    if locations:
        return render_template('locations.html', locations = locations)
    else:
        msg='No locations found'
        return render_template('locations.html', msg=msg)


@app.route('/product_movements')
def product_movements():

    sql = "SELECT * FROM PRODUCTMOVEMENTS"
    stmt = ibm_db.prepare(conn,sql)
    ibm_db.execute(stmt)
    products_mov = ibm_db.fetch_tuple(stmt)
    # print(products_tup["LOCATION_ID"])
    result = []
    
    while(products_mov):
        result.append(products_mov)
        products_mov = ibm_db.fetch_tuple(stmt)

    # print(result)

    if result:
        return render_template('product_movements.html', movements = result)
    else:
        msg='No product movements found'
        return render_template('product_movements.html', msg=msg)


class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=1, max=25)])
    email = StringField('Email', [validators.length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')

@app.route('/register', methods=['GET','POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        sql = "INSERT INTO USERS(NAME,EMAIL,USERNAME,PASSWORD) VALUES(?,?,?,?)"
        stmt = ibm_db.prepare(conn,sql)
        ibm_db.bind_param(stmt,1,name)
        ibm_db.bind_param(stmt,2,email)
        ibm_db.bind_param(stmt,3,username)
        ibm_db.bind_param(stmt,4,password)
        ibm_db.execute(stmt)
        
        flash("You are now registered and can log in", "success")
        return redirect(url_for('login'))
    return render_template('register.html', form = form)


@app.route('/login', methods = ['GET', 'POST'])
def login():
    if request.method == 'POST':

        username = request.form['username']
        password_candidate = request.form['password']

        sql = "SELECT * FROM USERS WHERE USERNAME = ?"
        stmt = ibm_db.prepare(conn,sql)
        ibm_db.bind_param(stmt,1,username)
        ibm_db.execute(stmt)
        result = ibm_db.fetch_assoc(stmt)

        if result:
            password = result["PASSWORD"]
            print(password_candidate,password)
 
            if sha256_crypt.verify(request.form['password'],  password):
                session['logged_in'] = True
                session['username'] = username

                flash("you are now logged in","success")
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid Login'
                return render_template('login.html', error=error)

        else:
            error = 'Username not found'
            return render_template('login.html', error=error)
    return render_template('login.html')

def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login','danger')
            return redirect(url_for('login'))
    return wrap


@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash("You are now logged out", "success")
    return redirect(url_for('login'))


@app.route('/dashboard')
@is_logged_in
def dashboard():

    sql = "SELECT PRODUCT_ID,LOCATION_ID,QTY FROM PRODUCT_BALANCE"
    stmt = ibm_db.prepare(conn,sql)
    ibm_db.execute(stmt)
    products_tup = ibm_db.fetch_tuple(stmt)
    products = []
    
    while(products_tup):
        products.append(products_tup)
        products_tup = ibm_db.fetch_tuple(stmt)

    sql = "SELECT LOCATION_ID FROM lOCATIONS"
    stmt = ibm_db.prepare(conn,sql)
    ibm_db.execute(stmt)
    locations = ibm_db.fetch_assoc(stmt)
    locs = []

    while(locations):
        locs.append(locations["LOCATION_ID"])
        locations = ibm_db.fetch_assoc(stmt)

    # print(locs)

    if products:
        return render_template('dashboard.html', products = products, locations = locs)
    else:
        msg='No products found'
        return render_template('dashboard.html', msg=msg)

class ProductForm(Form):
    product_id = StringField('Product ID', [validators.Length(min=1, max=200)])


@app.route('/add_product', methods=['GET', 'POST'])
@is_logged_in
def add_product():
    form = ProductForm(request.form)
    if request.method == 'POST' and form.validate():
        product_id = form.product_id.data

        sql = "INSERT INTO PRODUCTS VALUES(?)"
        stmt = ibm_db.prepare(conn,sql)
        ibm_db.bind_param(stmt,1,product_id)
        ibm_db.execute(stmt)

        flash("Product Added", "success")
        return redirect(url_for('products'))

    return render_template('add_product.html', form=form)


@app.route('/edit_product/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_product(id):

    sql = "SELECT * FROM PRODUCTS WHERE PRODUCT_ID = ?"
    stmt = ibm_db.prepare(conn,sql)
    ibm_db.bind_param(stmt,1,id)
    ibm_db.execute(stmt)
    product = ibm_db.fetch_assoc(stmt)

    form = ProductForm(request.form)

    form.product_id.data = product['PRODUCT_ID']

    if request.method == 'POST' and form.validate():
        product_id = request.form['product_id']

        sql = "UPDATE PRODUCTS SET PRODUCT_ID = ? WHERE PRODUCT_ID=?"
        stmt = ibm_db.prepare(conn,sql)
        ibm_db.bind_param(stmt,1,product_id)
        ibm_db.bind_param(stmt,2,id)
        ibm_db.execute(stmt)

        flash("Product Updated", "success")
        return redirect(url_for('products'))

    return render_template('edit_product.html', form=form)

@app.route('/delete_product/<string:id>', methods=['POST'])
@is_logged_in
def delete_product(id):

    sql = "DELETE FROM PRODUCTS WHERE PRODUCT_ID=?"
    stmt = ibm_db.prepare(conn,sql)
    ibm_db.bind_param(stmt,1,id)
    ibm_db.execute(stmt)

    flash("Product Deleted", "success")

    return redirect(url_for('products'))


class LocationForm(Form):
    location_id = StringField('Location ID', [validators.Length(min=1, max=200)])

@app.route('/add_location', methods=['GET', 'POST'])
@is_logged_in
def add_location():
    form = LocationForm(request.form)
    if request.method == 'POST' and form.validate():
        location_id = form.location_id.data

        sql = "INSERT INTO LOCATIONS VALUES(?)"
        stmt = ibm_db.prepare(conn,sql)
        ibm_db.bind_param(stmt,1,location_id)
        ibm_db.execute(stmt)

        flash("Location Added", "success")
        return redirect(url_for('locations'))

    return render_template('add_location.html', form=form)


@app.route('/edit_location/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_location(id):

    sql = "SELECT * FROM LOCATIONS WHERE LOCATION_ID = ?"
    stmt = ibm_db.prepare(conn,sql)
    ibm_db.bind_param(stmt,1,id)
    ibm_db.execute(stmt)
    location = ibm_db.fetch_assoc(stmt)

    form = LocationForm(request.form)

    form.location_id.data = location['LOCATION_ID']

    if request.method == 'POST' and form.validate():
        location_id = request.form['location_id']

        sql = "UPDATE LOCATIONS SET LOCATION_ID = ? WHERE LOCATION_ID=?"
        stmt = ibm_db.prepare(conn,sql)
        ibm_db.bind_param(stmt,1,location_id)
        ibm_db.bind_param(stmt,2,id)
        ibm_db.execute(stmt)


        flash("Location Updated", "success")
        return redirect(url_for('locations'))

    return render_template('edit_location.html', form=form)

@app.route('/delete_location/<string:id>', methods=['POST'])
@is_logged_in
def delete_location(id):
    
    sql = "DELETE FROM LOCATIONS WHERE LOCATION_ID=?"
    stmt = ibm_db.prepare(conn,sql)
    ibm_db.bind_param(stmt,1,id)
    ibm_db.execute(stmt)

    flash("Location Deleted", "success")

    return redirect(url_for('locations'))


class ProductMovementForm(Form):
    from_location = SelectField('From Location', choices=[])
    to_location = SelectField('To Location', choices=[])
    product_id = SelectField('Product ID', choices=[])
    qty = IntegerField('Quantity')


@app.route('/add_product_movements', methods=['GET', 'POST'])
@is_logged_in
def add_product_movements():
    form = ProductMovementForm(request.form) 

    sql = "SELECT PRODUCT_ID FROM PRODUCTS"
    stmt = ibm_db.prepare(conn,sql)
    ibm_db.execute(stmt)
    products = ibm_db.fetch_assoc(stmt)
    prods = []
    
    while(products):
        prods.append(products['PRODUCT_ID'])
        products = ibm_db.fetch_assoc(stmt)
    # print(prods)
    
    sql = "SELECT LOCATION_ID FROM LOCATIONS"
    stmt = ibm_db.prepare(conn,sql)
    ibm_db.execute(stmt)
    locations = ibm_db.fetch_assoc(stmt)
    locs = []
    
    while(locations):
        locs.append(locations['LOCATION_ID'])
        locations = ibm_db.fetch_assoc(stmt)
    # print(locs)

    form.from_location.choices = [(l,l) for l in locs]
    form.from_location.choices.append(("--","--"))
    form.to_location.choices = [(l,l) for l in locs]
    form.to_location.choices.append(("--","--"))
    form.product_id.choices = [(p,p) for p in prods]
    if request.method == 'POST' and form.validate():
        from_location = form.from_location.data
        to_location = form.to_location.data
        product_id = form.product_id.data
        qty = form.qty.data
    
        sql = "INSERT INTO PRODUCTMOVEMENTS(FROM_LOCATION,TO_LOCATION,PRODUCT_ID,QTY) VALUES(?,?,?,?)"
        stmt = ibm_db.prepare(conn,sql)
        ibm_db.bind_param(stmt,1,from_location)
        ibm_db.bind_param(stmt,2,to_location)
        ibm_db.bind_param(stmt,3,product_id)
        ibm_db.bind_param(stmt,4,qty)
        ibm_db.execute(stmt)

        if from_location == "--":
            sql = "SELECT * FROM PRODUCT_BALANCE WHERE LOCATION_ID = ? AND PRODUCT_ID = ?"
            stmt = ibm_db.prepare(conn,sql)
            ibm_db.bind_param(stmt,1,to_location)
            ibm_db.bind_param(stmt,2,product_id)
            ibm_db.execute(stmt)
            result = ibm_db.fetch_assoc(stmt)

            if result!=None:
                if result:
                    Quantity = result["QTY"]
                    q = Quantity + qty 

                    sql = "UPDATE PRODUCT_BALANCE SET QTY=? WHERE LOCATION_ID=? and PRODUCT_ID=?"
                    stmt = ibm_db.prepare(conn,sql)
                    ibm_db.bind_param(stmt,1,q)
                    ibm_db.bind_param(stmt,2,to_location)
                    ibm_db.bind_param(stmt,3,product_id)
                    ibm_db.execute(stmt)
            else:
                sql = "INSERT INTO PRODUCT_BALANCE(PRODUCT_ID,LOCATION_ID,QTY) VALUES(?,?,?)"
                stmt = ibm_db.prepare(conn,sql)
                ibm_db.bind_param(stmt,1,product_id)
                ibm_db.bind_param(stmt,2,to_location)
                ibm_db.bind_param(stmt,3,qty)
                ibm_db.execute(stmt)

        elif to_location == "--":
            sql = "SELECT * FROM PRODUCT_BALANCE WHERE LOCATION_ID = ? AND PRODUCT_ID = ?"
            stmt = ibm_db.prepare(conn,sql)
            ibm_db.bind_param(stmt,1,from_location)
            ibm_db.bind_param(stmt,2,product_id)
            ibm_db.execute(stmt)
            result = ibm_db.fetch_assoc(stmt)

            if result!=None:
                if result:
                    Quantity = result["QTY"]
                    q = Quantity - qty 
                    sql = "UPDATE PRODUCT_BALANCE SET QTY=? WHERE LOCATION_ID=? and PRODUCT_ID=?"
                    stmt = ibm_db.prepare(conn,sql)
                    ibm_db.bind_param(stmt,1,q)
                    ibm_db.bind_param(stmt,2,from_location)
                    ibm_db.bind_param(stmt,3,product_id)
                    ibm_db.execute(stmt)
                   
            else:
                sql = "INSERT INTO PRODUCT_BALANCE(PRODUCT_ID,LOCATION_ID,QTY) VALUES(?,?,?)"
                stmt = ibm_db.prepare(conn,sql)
                ibm_db.bind_param(stmt,1,product_id)
                ibm_db.bind_param(stmt,2,from_location)
                ibm_db.bind_param(stmt,3,qty)
                ibm_db.execute(stmt)
                
        else:
          
            sql = "SELECT * FROM PRODUCT_BALANCE WHERE LOCATION_ID = ? AND PRODUCT_ID = ?"
            stmt = ibm_db.prepare(conn,sql)
            ibm_db.bind_param(stmt,1,to_location)
            ibm_db.bind_param(stmt,2,product_id)
            ibm_db.execute(stmt)
            result = ibm_db.fetch_assoc(stmt)

            if result!=None:
                    Quantity = result["QTY"]
                    q = Quantity + qty 

                    sql = "UPDATE PRODUCT_BALANCE SET QTY=? WHERE LOCATION_ID=? and PRODUCT_ID=?"
                    stmt = ibm_db.prepare(conn,sql)
                    ibm_db.bind_param(stmt,1,q)
                    ibm_db.bind_param(stmt,2,to_location)
                    ibm_db.bind_param(stmt,3,product_id)
                    ibm_db.execute(stmt)

            else:
                sql = "INSERT INTO PRODUCT_BALANCE(PRODUCT_ID,LOCATION_ID,QTY) VALUES(?,?,?)"
                stmt = ibm_db.prepare(conn,sql)
                ibm_db.bind_param(stmt,1,product_id)
                ibm_db.bind_param(stmt,2,to_location)
                ibm_db.bind_param(stmt,3,qty)
                ibm_db.execute(stmt)

            sql = "SELECT * FROM PRODUCT_BALANCE WHERE LOCATION_ID = ? AND PRODUCT_ID = ?"
            stmt = ibm_db.prepare(conn,sql)
            ibm_db.bind_param(stmt,1,from_location)
            ibm_db.bind_param(stmt,2,product_id)
            ibm_db.execute(stmt)
            result = ibm_db.fetch_assoc(stmt)
            if result!=None:
                if result:
                    Quantity = result["QTY"]
                    q = Quantity - qty 
                    sql = "UPDATE PRODUCT_BALANCE SET QTY=? WHERE LOCATION_ID=? and PRODUCT_ID=?"
                    stmt = ibm_db.prepare(conn,sql)
                    ibm_db.bind_param(stmt,1,q)
                    ibm_db.bind_param(stmt,2,from_location)
                    ibm_db.bind_param(stmt,3,product_id)
                    ibm_db.execute(stmt)
                    print("Yes")
                    
            else:
               
                sql = "INSERT INTO PRODUCT_BALANCE(PRODUCT_ID,LOCATION_ID,QTY) VALUES(?,?,?)"
                stmt = ibm_db.prepare(conn,sql)
                ibm_db.bind_param(stmt,1,product_id)
                ibm_db.bind_param(stmt,2,from_location)
                ibm_db.bind_param(stmt,3,qty)
                ibm_db.execute(stmt)
                print("No")

        sql = "SELECT * FROM PRODUCT_BALANCE"
        stmt = ibm_db.prepare(conn,sql)
        ibm_db.execute(stmt)
        products = ibm_db.fetch_assoc(stmt)
        prod_ = []
        locs_ = []
        qty_ = []
        low_msg = "Dear User,\n"
        flag = 0
        while(products):
            prod_.append(products['PRODUCT_ID'])
            locs_.append(products['LOCATION_ID'])
            qty_.append(products['QTY'])
            products = ibm_db.fetch_assoc(stmt)

        for i in range(0,len(prod_)):
            if qty_[i] <= 30:
                low_msg = low_msg + "Your Product - " + prod_[i] + " at the warehouse " + locs_[i] + " is very low!!! \n"
                flag = 1
        
        if flag==1:    
            mail_from = '19i317@psgtech.ac.in'
            mail_to = '19i323@psgtech.ac.in'

            msg = MIMEMultipart()
            msg['From'] = mail_from
            msg['To'] = mail_to
            msg['Subject'] = 'Low Product Alert!!!'
            mail_body = low_msg + "Please keep Track of your product. "
            msg.attach(MIMEText(mail_body))

            try:
                server = smtplib.SMTP_SSL('smtp.sendgrid.net', 465)
                server.ehlo()
                server.login('apikey', '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')
                server.sendmail(mail_from, mail_to, msg.as_string())
                server.close()
                print("mail sent")
            except:
                print("issue")
            
        flash("Product Movement Added", "success")


        return redirect(url_for('product_movements'))

    return render_template('add_product_movements.html', form=form)


@app.route('/edit_product_movement/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_product_movements(id):
    form = ProductMovementForm(request.form) 

    sql = "SELECT PRODUCT_ID FROM PRODUCTS"
    stmt = ibm_db.prepare(conn,sql)
    ibm_db.execute(stmt)
    products = ibm_db.fetch_assoc(stmt)
    prods = []
    
    while(products):
        prods.append(products['PRODUCT_ID'])
        products = ibm_db.fetch_assoc(stmt)
    print(prods)

    
    sql = "SELECT LOCATION_ID FROM LOCATIONS"
    stmt = ibm_db.prepare(conn,sql)
    ibm_db.execute(stmt)
    locations = ibm_db.fetch_assoc(stmt)
    locs = []
    
    while(locations):
        locs.append(locations['LOCATION_ID'])
        locations = ibm_db.fetch_assoc(stmt)
    print(locs)

    form.from_location.choices = [(l,l) for l in locs]
    form.from_location.choices.append(("--","--"))
    form.to_location.choices = [(l,l) for l in locs]
    form.to_location.choices.append(("--","--"))
    form.product_id.choices = [(p,p) for p in prods]

    sql = "SELECT * FROM PRODUCTMOVEMENTS WHERE MOVEMENT_ID= ?"
    stmt = ibm_db.prepare(conn,sql)
    ibm_db.bind_param(stmt,1,id)
    ibm_db.execute(stmt)
    movement = ibm_db.fetch_assoc(stmt)

    form.from_location.data = movement['FROM_LOCATION']
    form.to_location.data = movement['TO_LOCATION']
    form.product_id.data = movement['PRODUCT_ID']
    form.qty.data = movement['QTY']
    
    if request.method == 'POST' and form.validate():
        from_location = request.form['from_location']
        to_location = request.form['to_location']
        product_id = request.form['product_id']
        qty = int(request.form['qty'])
        print("h")
        sql = "UPDATE PRODUCTMOVEMENTS SET FROM_LOCATION=?, TO_LOCATION=?, PRODUCT_ID=?, QTY=? WHERE MOVEMENT_ID=?"
        stmt = ibm_db.prepare(conn,sql)
        ibm_db.bind_param(stmt,1,from_location)
        ibm_db.bind_param(stmt,2,to_location)
        ibm_db.bind_param(stmt,3,product_id)
        ibm_db.bind_param(stmt,4,qty)
        ibm_db.bind_param(stmt,5,id)
        ibm_db.execute(stmt)

        if from_location == "--":
            sql = "SELECT * FROM PRODUCT_BALANCE WHERE LOCATION_ID = ? AND PRODUCT_ID = ?"
            stmt = ibm_db.prepare(conn,sql)
            ibm_db.bind_param(stmt,1,to_location)
            ibm_db.bind_param(stmt,2,product_id)
            ibm_db.execute(stmt)
            result = ibm_db.fetch_assoc(stmt)

            if result!=None:
                if result:
                    Quantity = result["QTY"]
                    q = Quantity + qty 
                    sql = "UPDATE PRODUCT_BALANCE SET QTY=? WHERE LOCATION_ID=? and PRODUCT_ID=?"
                    stmt = ibm_db.prepare(conn,sql)
                    ibm_db.bind_param(stmt,1,q)
                    ibm_db.bind_param(stmt,2,to_location)
                    ibm_db.bind_param(stmt,3,product_id)
                    ibm_db.execute(stmt)
                   
            else:
                sql = "INSERT INTO PRODUCT_BALANCE(PRODUCT_ID,LOCATION_ID,QTY) VALUES(?,?,?)"
                stmt = ibm_db.prepare(conn,sql)
                ibm_db.bind_param(stmt,1,product_id)
                ibm_db.bind_param(stmt,2,to_location)
                ibm_db.bind_param(stmt,3,qty)
                ibm_db.execute(stmt)
                
        elif to_location == "--":
            sql = "SELECT * FROM PRODUCT_BALANCE WHERE LOCATION_ID = ? AND PRODUCT_ID = ?"
            stmt = ibm_db.prepare(conn,sql)
            ibm_db.bind_param(stmt,1,from_location)
            ibm_db.bind_param(stmt,2,product_id)
            ibm_db.execute(stmt)
            result = ibm_db.fetch_assoc(stmt)

            if result!=None:
                if result:
                    Quantity = result["QTY"]
                    q = Quantity - qty 
                    sql = "UPDATE PRODUCT_BALANCE SET QTY=? WHERE LOCATION_ID=? and PRODUCT_ID=?"
                    stmt = ibm_db.prepare(conn,sql)
                    ibm_db.bind_param(stmt,1,q)
                    ibm_db.bind_param(stmt,2,from_location)
                    ibm_db.bind_param(stmt,3,product_id)
                    ibm_db.execute(stmt)
            else:
                sql = "INSERT INTO PRODUCT_BALANCE(PRODUCT_ID,LOCATION_ID,QTY) VALUES(?,?,?)"
                stmt = ibm_db.prepare(conn,sql)
                ibm_db.bind_param(stmt,1,product_id)
                ibm_db.bind_param(stmt,2,from_location)
                ibm_db.bind_param(stmt,3,qty)
                ibm_db.execute(stmt)
                
        else:
            sql = "SELECT * FROM PRODUCT_BALANCE WHERE LOCATION_ID = ? AND PRODUCT_ID = ?"
            stmt = ibm_db.prepare(conn,sql)
            ibm_db.bind_param(stmt,1,to_location)
            ibm_db.bind_param(stmt,2,product_id)
            ibm_db.execute(stmt)
            result = ibm_db.fetch_assoc(stmt)

            if result!=None:
                    Quantity = result["QTY"]
                    q = Quantity + qty 

                    sql = "UPDATE PRODUCT_BALANCE SET QTY=? WHERE LOCATION_ID=? and PRODUCT_ID=?"
                    stmt = ibm_db.prepare(conn,sql)
                    ibm_db.bind_param(stmt,1,q)
                    ibm_db.bind_param(stmt,2,to_location)
                    ibm_db.bind_param(stmt,3,product_id)
                    ibm_db.execute(stmt)
            else:
                sql = "INSERT INTO PRODUCT_BALANCE(PRODUCT_ID,LOCATION_ID,QTY) VALUES(?,?,?)"
                stmt = ibm_db.prepare(conn,sql)
                ibm_db.bind_param(stmt,1,product_id)
                ibm_db.bind_param(stmt,2,to_location)
                ibm_db.bind_param(stmt,3,qty)
                ibm_db.execute(stmt)

            sql = "SELECT * FROM PRODUCT_BALANCE WHERE LOCATION_ID = ? AND PRODUCT_ID = ?"
            stmt = ibm_db.prepare(conn,sql)
            ibm_db.bind_param(stmt,1,from_location)
            ibm_db.bind_param(stmt,2,product_id)
            ibm_db.execute(stmt)
            result = ibm_db.fetch_assoc(stmt)
            if result!=None:
                if result:
                    Quantity = result["QTY"]
                    q = Quantity - qty 
                    sql = "UPDATE PRODUCT_BALANCE SET QTY=? WHERE LOCATION_ID=? and PRODUCT_ID=?"
                    stmt = ibm_db.prepare(conn,sql)
                    ibm_db.bind_param(stmt,1,q)
                    ibm_db.bind_param(stmt,2,from_location)
                    ibm_db.bind_param(stmt,3,product_id)
                    ibm_db.execute(stmt)
                    
            else:
                sql = "INSERT INTO PRODUCT_BALANCE(PRODUCT_ID,LOCATION_ID,QTY) VALUES(?,?,?)"
                stmt = ibm_db.prepare(conn,sql)
                ibm_db.bind_param(stmt,1,product_id)
                ibm_db.bind_param(stmt,2,from_location)
                ibm_db.bind_param(stmt,3,qty)
                ibm_db.execute(stmt)
                 
        flash("Product Movement Updated", "success")
        return redirect(url_for('product_movements'))

    return render_template('edit_product_movements.html', form=form)


@app.route('/delete_product_movements/<string:id>', methods=['POST'])
@is_logged_in
def delete_product_movements(id):

    sql = "DELETE FROM PRODUCTMOVEMENTS WHERE MOVEMENT_ID=?"
    stmt = ibm_db.prepare(conn,sql)
    ibm_db.bind_param(stmt,1,id)
    ibm_db.execute(stmt)


    flash("Product Movement Deleted", "success")

    return redirect(url_for('product_movements'))

if __name__ == '__main__':
    app.secret_key = "a"
    app.run(debug=True)
