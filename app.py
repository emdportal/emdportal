import pandas as pd
import io
import os
from datetime import timedelta
from dotenv import load_dotenv
from supabase import create_client, Client
from functools import wraps
import secrets
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, make_response, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Load environment variables
load_dotenv()

app = Flask(__name__)
database_url = os.environ.get('DATABASE_URL')
if not database_url:
    raise ValueError("DATABASE_URL environment variable is not set. Please configure it in Railway.")
app.config['SQLALCHEMY_DATABASE_URI'] = database_url.replace('postgres://', 'postgresql://')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(16))
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# Initialize database
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Supabase setup
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Define database models
class GeneralInformation(db.Model):
    sn = db.Column(db.Integer, primary_key=True)
    region = db.Column(db.String(50))
    domain = db.Column(db.String(50))
    exchange_name = db.Column(db.String(100))
    exchange_lic = db.Column(db.String(50))
    flc = db.Column(db.String(50))
    site_category = db.Column(db.String(50))
    nes_installed = db.Column(db.Text)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    tower_available = db.Column(db.String(10))
    towers = db.relationship('Tower', backref='general_info', lazy=True, cascade="all, delete-orphan")
    power_info = db.relationship('PowerInformation', backref='general_info', uselist=False, cascade="all, delete-orphan")
    dgs = db.relationship('DGInformation', backref='general_info', lazy=True, cascade="all, delete-orphan")
    battery_banks = db.relationship('BatteryBank', backref='general_info', lazy=True, cascade="all, delete-orphan")
    ac_units = db.relationship('ACUnit', backref='general_info', lazy=True, cascade="all, delete-orphan")
    solar_info = db.relationship('SolarInformation', backref='general_info', uselist=False, cascade="all, delete-orphan")

class Tower(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    general_info_sn = db.Column(db.Integer, db.ForeignKey('general_information.sn'))
    tower_type_height = db.Column(db.String(50))

class PowerInformation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    general_info_sn = db.Column(db.Integer, db.ForeignKey('general_information.sn'))
    wapda_ref_number = db.Column(db.String(50))
    transformer_capacity = db.Column(db.String(50))
    transformer_earthing = db.Column(db.String(50))
    make_of_rectifier = db.Column(db.String(50))
    working_status = db.Column(db.Boolean)
    rectifier_capacity = db.Column(db.Float)
    no_of_modules = db.Column(db.Integer)
    capacity_of_each_module = db.Column(db.Float)
    working_modules = db.Column(db.Integer)
    faulty_modules = db.Column(db.Integer)
    space_for_new_modules = db.Column(db.Integer)
    name_of_nes_connected = db.Column(db.Text)
    load_of_individual_ne = db.Column(db.Float)
    grounding_of_rectifier = db.Column(db.Boolean)
    spd_in_rectifier = db.Column(db.Boolean)
    spd_model = db.Column(db.String(50))
    total_installed_spds = db.Column(db.Integer)
    no_of_faulty_spds = db.Column(db.Integer)

class DGInformation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    general_info_sn = db.Column(db.Integer, db.ForeignKey('general_information.sn'))
    installed_dg = db.Column(db.String(50))
    engine_make = db.Column(db.String(50))
    installation_year = db.Column(db.Integer)
    dg_status = db.Column(db.String(50))
    dg_starting_battery = db.Column(db.String(50))
    smart_switch_installed = db.Column(db.Boolean)
    ats_installed = db.Column(db.Boolean)
    ats_capacity = db.Column(db.String(50))
    name_of_faulty_ats_parts = db.Column(db.String(100))
    no_of_faulty_ats_parts = db.Column(db.Integer)
    load_on_dg_p1 = db.Column(db.Float)
    load_on_dg_p2 = db.Column(db.Float)
    load_on_dg_p3 = db.Column(db.Float)
    site_load_total = db.Column(db.Float)
    site_load_p1 = db.Column(db.Float)
    site_load_p2 = db.Column(db.Float)
    site_load_p3 = db.Column(db.Float)

class BatteryBank(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    general_info_sn = db.Column(db.Integer, db.ForeignKey('general_information.sn'))
    make_of_battery = db.Column(db.String(50))
    battery_capacity = db.Column(db.Float)
    battery_type = db.Column(db.String(50))
    no_of_cells_bank = db.Column(db.Integer)
    date_of_installation = db.Column(db.String(50))
    load_on_battery_bank = db.Column(db.Float)
    practical_backup_time = db.Column(db.Float)
    battery_installed_new_or_used = db.Column(db.String(50))
    battery_moved_from = db.Column(db.String(100))

class ACUnit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    general_info_sn = db.Column(db.Integer, db.ForeignKey('general_information.sn'))
    location_of_ac_unit = db.Column(db.String(100))
    working_status = db.Column(db.Boolean)
    ac_make = db.Column(db.String(50))
    capacity_tons = db.Column(db.Float)
    type_of_ac = db.Column(db.String(50))
    mount_type = db.Column(db.String(50))
    date_of_installation = db.Column(db.String(50))
    sequence_controller_installed = db.Column(db.Boolean)
    ac_load = db.Column(db.Float)
    total_ac_load = db.Column(db.Float)
    fault_nature_of_ac_unit = db.Column(db.String(100))
    estimate_to_repair_ac = db.Column(db.Float)

class SolarInformation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    general_info_sn = db.Column(db.Integer, db.ForeignKey('general_information.sn'))
    total_solar_size = db.Column(db.Float)
    pv_solar_panel_capacity = db.Column(db.Float)
    no_of_pv_panels_installed = db.Column(db.Integer)
    make_of_pv_panels = db.Column(db.String(50))
    charge_controller_make = db.Column(db.String(50))

# Custom login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_token = request.cookies.get('auth_token')
        if not auth_token:
            return redirect(url_for('login'))
        try:
            user = supabase.auth.get_user(auth_token)
            if not user.user:
                return redirect(url_for('login'))
            session['user_id'] = user.user.id
        except Exception:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].lower()
        password = request.form['password']
        try:
            user_data = supabase.table('users_info').select('user_id', 'region').eq('username', username).execute()
            if not user_data.data:
                flash('Invalid username')
                return redirect(url_for('login'))
            user_id = user_data.data[0]['user_id']
            region = user_data.data[0]['region']
            email = f"{username}@ptclgroup.com"
            response = supabase.auth.sign_in_with_password({"email": email, "password": password})
            if response.user and response.user.id == user_id:
                access_token = response.session.access_token
                session['region'] = region
                session['username'] = username  # Store username in session
                resp = make_response(redirect(url_for('index')))
                resp.set_cookie('auth_token', access_token, httponly=True, secure=True, samesite='Lax')
                return resp
            else:
                error = response.error.message if hasattr(response, 'error') and response.error else 'Unknown error'
                flash(f'Login failed: {error}')
        except Exception as e:
            flash('Login failed: ' + str(e))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    resp = make_response(redirect(url_for('login')))
    resp.set_cookie('auth_token', '', expires=0)
    session.pop('region', None)
    session.pop('username', None)
    supabase.auth.sign_out()
    return resp

@app.route('/')
@login_required
def index():
    try:
        user_region = session.get('region')
        if user_region == "All":
            exchanges = GeneralInformation.query.all()
        else:
            exchanges = GeneralInformation.query.filter_by(region=user_region).all()
        
        regions = db.session.query(GeneralInformation.region, db.func.count(GeneralInformation.sn)).group_by(GeneralInformation.region).all()
        region_labels = [r[0] for r in regions if r[0] is not None]
        region_counts = [r[1] for r in regions if r[0] is not None]
        total_exchanges = len(exchanges)
        year_counts = [total_exchanges // 2, total_exchanges - (total_exchanges // 2)]
        return render_template('index.html', 
                             exchanges=exchanges, 
                             region_labels=region_labels, 
                             region_counts=region_counts, 
                             year_counts=year_counts, 
                             username=session.get('username', 'User'))
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        try:
            sn = int(request.form['sn'])
            existing_exchange = GeneralInformation.query.get(sn)
            if existing_exchange:
                flash('SN already exists. Please use a different SN.')
                return redirect(url_for('add'))

            general = GeneralInformation(
                sn=sn,
                region=request.form['region'],
                domain=request.form['domain'],
                exchange_name=request.form['exchange_name'],
                exchange_lic=request.form['exchange_lic'],
                flc=request.form['flc'],
                site_category=request.form['site_category'],
                nes_installed=request.form['nes_installed'],
                latitude=float(request.form['latitude']) if request.form['latitude'] else None,
                longitude=float(request.form['longitude']) if request.form['longitude'] else None,
                tower_available=request.form['tower_available']
            )

            # Tower Information
            if general.tower_available == 'Yes':
                tower_types = request.form.getlist('tower_type_height[]')
                for tower_type in tower_types:
                    if tower_type:
                        tower = Tower(tower_type_height=tower_type)
                        general.towers.append(tower)

            # Power Information
            power_info = PowerInformation(
                wapda_ref_number=request.form['wapda_ref_number'],
                transformer_capacity=request.form['transformer_capacity'],
                transformer_earthing=request.form['transformer_earthing'],
                make_of_rectifier=request.form['make_of_rectifier'],
                working_status='working_status_power' in request.form,
                rectifier_capacity=float(request.form['rectifier_capacity']) if request.form['rectifier_capacity'] else None,
                no_of_modules=int(request.form['no_of_modules']) if request.form['no_of_modules'] else None,
                capacity_of_each_module=float(request.form['capacity_of_each_module']) if request.form['capacity_of_each_module'] else None,
                working_modules=int(request.form['working_modules']) if request.form['working_modules'] else None,
                faulty_modules=int(request.form['faulty_modules']) if request.form['faulty_modules'] else None,
                space_for_new_modules=int(request.form['space_for_new_modules']) if request.form['space_for_new_modules'] else None,
                name_of_nes_connected=request.form['name_of_nes_connected'],
                load_of_individual_ne=float(request.form['load_of_individual_ne']) if request.form['load_of_individual_ne'] else None,
                grounding_of_rectifier='grounding_of_rectifier' in request.form,
                spd_in_rectifier='spd_in_rectifier' in request.form,
                spd_model=request.form['spd_model'],
                total_installed_spds=int(request.form['total_installed_spds']) if request.form['total_installed_spds'] else None,
                no_of_faulty_spds=int(request.form['no_of_faulty_spds']) if request.form['no_of_faulty_spds'] else None
            )
            general.power_info = power_info

            # DG Information
            installed_dgs = request.form.getlist('installed_dg[]')
            for i in range(len(installed_dgs)):
                if installed_dgs[i]:
                    dg = DGInformation(
                        installed_dg=installed_dgs[i],
                        engine_make=request.form.getlist('engine_make[]')[i],
                        installation_year=int(request.form.getlist('installation_year[]')[i]) if request.form.getlist('installation_year[]')[i] else None,
                        dg_status=request.form.getlist('dg_status[]')[i],
                        dg_starting_battery=request.form.getlist('dg_starting_battery[]')[i],
                        smart_switch_installed=f"smart_switch_installed_{i}" in request.form.getlist('smart_switch_installed[]'),
                        ats_installed=f"ats_installed_{i}" in request.form.getlist('ats_installed[]'),
                        ats_capacity=request.form.getlist('ats_capacity[]')[i],
                        name_of_faulty_ats_parts=request.form.getlist('name_of_faulty_ats_parts[]')[i],
                        no_of_faulty_ats_parts=int(request.form.getlist('no_of_faulty_ats_parts[]')[i]) if request.form.getlist('no_of_faulty_ats_parts[]')[i] else None,
                        load_on_dg_p1=float(request.form.getlist('load_on_dg_p1[]')[i]) if request.form.getlist('load_on_dg_p1[]')[i] else None,
                        load_on_dg_p2=float(request.form.getlist('load_on_dg_p2[]')[i]) if request.form.getlist('load_on_dg_p2[]')[i] else None,
                        load_on_dg_p3=float(request.form.getlist('load_on_dg_p3[]')[i]) if request.form.getlist('load_on_dg_p3[]')[i] else None,
                        site_load_total=float(request.form.getlist('site_load_total[]')[i]) if request.form.getlist('site_load_total[]')[i] else None,
                        site_load_p1=float(request.form.getlist('site_load_p1[]')[i]) if request.form.getlist('site_load_p1[]')[i] else None,
                        site_load_p2=float(request.form.getlist('site_load_p2[]')[i]) if request.form.getlist('site_load_p2[]')[i] else None,
                        site_load_p3=float(request.form.getlist('site_load_p3[]')[i]) if request.form.getlist('site_load_p3[]')[i] else None
                    )
                    general.dgs.append(dg)

            # Battery Bank Information
            makes_of_battery = request.form.getlist('make_of_battery[]')
            for i in range(len(makes_of_battery)):
                if makes_of_battery[i]:
                    battery = BatteryBank(
                        make_of_battery=makes_of_battery[i],
                        battery_capacity=float(request.form.getlist('battery_capacity[]')[i]) if request.form.getlist('battery_capacity[]')[i] else None,
                        battery_type=request.form.getlist('battery_type[]')[i],
                        no_of_cells_bank=int(request.form.getlist('no_of_cells_bank[]')[i]) if request.form.getlist('no_of_cells_bank[]')[i] else None,
                        date_of_installation=request.form.getlist('date_of_installation_battery[]')[i],
                        load_on_battery_bank=float(request.form.getlist('load_on_battery_bank[]')[i]) if request.form.getlist('load_on_battery_bank[]')[i] else None,
                        practical_backup_time=float(request.form.getlist('practical_backup_time[]')[i]) if request.form.getlist('practical_backup_time[]')[i] else None,
                        battery_installed_new_or_used=request.form.getlist('battery_installed_new_or_used[]')[i],
                        battery_moved_from=request.form.getlist('battery_moved_from[]')[i]
                    )
                    general.battery_banks.append(battery)

            # AC Unit Information
            locations = request.form.getlist('location_of_ac_unit[]')
            for i in range(len(locations)):
                if locations[i]:
                    ac = ACUnit(
                        location_of_ac_unit=locations[i],
                        working_status=f"working_status_ac_{i}" in request.form.getlist('working_status_ac[]'),
                        ac_make=request.form.getlist('ac_make[]')[i],
                        capacity_tons=float(request.form.getlist('capacity_tons[]')[i]) if request.form.getlist('capacity_tons[]')[i] else None,
                        type_of_ac=request.form.getlist('type_of_ac[]')[i],
                        mount_type=request.form.getlist('mount_type[]')[i],
                        date_of_installation=request.form.getlist('date_of_installation_ac[]')[i],
                        sequence_controller_installed=f"sequence_controller_installed_{i}" in request.form.getlist('sequence_controller_installed[]'),
                        ac_load=float(request.form.getlist('ac_load[]')[i]) if request.form.getlist('ac_load[]')[i] else None,
                        total_ac_load=float(request.form.getlist('total_ac_load[]')[i]) if request.form.getlist('total_ac_load[]')[i] else None,
                        fault_nature_of_ac_unit=request.form.getlist('fault_nature_of_ac_unit[]')[i],
                        estimate_to_repair_ac=float(request.form.getlist('estimate_to_repair_ac[]')[i]) if request.form.getlist('estimate_to_repair_ac[]')[i] else None
                    )
                    general.ac_units.append(ac)

            # Solar Information
            solar_info = SolarInformation(
                total_solar_size=float(request.form['total_solar_size']) if request.form['total_solar_size'] else None,
                pv_solar_panel_capacity=float(request.form['pv_solar_panel_capacity']) if request.form['pv_solar_panel_capacity'] else None,
                no_of_pv_panels_installed=int(request.form['no_of_pv_panels_installed']) if request.form['no_of_pv_panels_installed'] else None,
                make_of_pv_panels=request.form['make_of_pv_panels'],
                charge_controller_make=request.form['charge_controller_make']
            )
            general.solar_info = solar_info

            db.session.add(general)
            db.session.commit()
            flash('Exchange added successfully!')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding exchange: {str(e)}')
            return redirect(url_for('add'))
    return render_template('form.html', general=None, username=session.get('username', 'User'))

@app.route('/edit/<int:sn>', methods=['GET', 'POST'])
@login_required
def edit(sn):
    general = GeneralInformation.query.get_or_404(sn)
    user_region = session.get('region')
    
    # Restrict access based on region
    if user_region != "All" and general.region != user_region:
        flash('You do not have access to edit this exchange.')
        return redirect(url_for('index'))

    if request.method == 'POST':
        try:
            # Update General Information
            general.region = request.form['region']
            general.domain = request.form['domain']
            general.exchange_name = request.form['exchange_name']
            general.exchange_lic = request.form['exchange_lic']
            general.flc = request.form['flc']
            general.site_category = request.form['site_category']
            general.nes_installed = request.form['nes_installed']
            general.latitude = float(request.form['latitude']) if request.form['latitude'] else None
            general.longitude = float(request.form['longitude']) if request.form['longitude'] else None
            general.tower_available = request.form['tower_available']

            # Update Towers
            if general.tower_available == 'Yes':
                general.towers = []
                tower_types = request.form.getlist('tower_type_height[]')
                for tower_type in tower_types:
                    if tower_type:
                        tower = Tower(tower_type_height=tower_type)
                        general.towers.append(tower)
            else:
                general.towers = []

            # Update Power Information
            if not general.power_info:
                general.power_info = PowerInformation()
            general.power_info.wapda_ref_number = request.form['wapda_ref_number']
            general.power_info.transformer_capacity = request.form['transformer_capacity']
            general.power_info.transformer_earthing = request.form['transformer_earthing']
            general.power_info.make_of_rectifier = request.form['make_of_rectifier']
            general.power_info.working_status = 'working_status_power' in request.form
            general.power_info.rectifier_capacity = float(request.form['rectifier_capacity']) if request.form['rectifier_capacity'] else None
            general.power_info.no_of_modules = int(request.form['no_of_modules']) if request.form['no_of_modules'] else None
            general.power_info.capacity_of_each_module = float(request.form['capacity_of_each_module']) if request.form['capacity_of_each_module'] else None
            general.power_info.working_modules = int(request.form['working_modules']) if request.form['working_modules'] else None
            general.power_info.faulty_modules = int(request.form['faulty_modules']) if request.form['faulty_modules'] else None
            general.power_info.space_for_new_modules = int(request.form['space_for_new_modules']) if request.form['space_for_new_modules'] else None
            general.power_info.name_of_nes_connected = request.form['name_of_nes_connected']
            general.power_info.load_of_individual_ne = float(request.form['load_of_individual_ne']) if request.form['load_of_individual_ne'] else None
            general.power_info.grounding_of_rectifier = 'grounding_of_rectifier' in request.form
            general.power_info.spd_in_rectifier = 'spd_in_rectifier' in request.form
            general.power_info.spd_model = request.form['spd_model']
            general.power_info.total_installed_spds = int(request.form['total_installed_spds']) if request.form['total_installed_spds'] else None
            general.power_info.no_of_faulty_spds = int(request.form['no_of_faulty_spds']) if request.form['no_of_faulty_spds'] else None

            # Update DG Information
            general.dgs = []
            installed_dgs = request.form.getlist('installed_dg[]')
            for i in range(len(installed_dgs)):
                if installed_dgs[i]:
                    dg = DGInformation(
                        installed_dg=installed_dgs[i],
                        engine_make=request.form.getlist('engine_make[]')[i],
                        installation_year=int(request.form.getlist('installation_year[]')[i]) if request.form.getlist('installation_year[]')[i] else None,
                        dg_status=request.form.getlist('dg_status[]')[i],
                        dg_starting_battery=request.form.getlist('dg_starting_battery[]')[i],
                        smart_switch_installed=f"smart_switch_installed_{i}" in request.form.getlist('smart_switch_installed[]'),
                        ats_installed=f"ats_installed_{i}" in request.form.getlist('ats_installed[]'),
                        ats_capacity=request.form.getlist('ats_capacity[]')[i],
                        name_of_faulty_ats_parts=request.form.getlist('name_of_faulty_ats_parts[]')[i],
                        no_of_faulty_ats_parts=int(request.form.getlist('no_of_faulty_ats_parts[]')[i]) if request.form.getlist('no_of_faulty_ats_parts[]')[i] else None,
                        load_on_dg_p1=float(request.form.getlist('load_on_dg_p1[]')[i]) if request.form.getlist('load_on_dg_p1[]')[i] else None,
                        load_on_dg_p2=float(request.form.getlist('load_on_dg_p2[]')[i]) if request.form.getlist('load_on_dg_p2[]')[i] else None,
                        load_on_dg_p3=float(request.form.getlist('load_on_dg_p3[]')[i]) if request.form.getlist('load_on_dg_p3[]')[i] else None,
                        site_load_total=float(request.form.getlist('site_load_total[]')[i]) if request.form.getlist('site_load_total[]')[i] else None,
                        site_load_p1=float(request.form.getlist('site_load_p1[]')[i]) if request.form.getlist('site_load_p1[]')[i] else None,
                        site_load_p2=float(request.form.getlist('site_load_p2[]')[i]) if request.form.getlist('site_load_p2[]')[i] else None,
                        site_load_p3=float(request.form.getlist('site_load_p3[]')[i]) if request.form.getlist('site_load_p3[]')[i] else None
                    )
                    general.dgs.append(dg)

            # Update Battery Bank Information
            general.battery_banks = []
            makes_of_battery = request.form.getlist('make_of_battery[]')
            for i in range(len(makes_of_battery)):
                if makes_of_battery[i]:
                    battery = BatteryBank(
                        make_of_battery=makes_of_battery[i],
                        battery_capacity=float(request.form.getlist('battery_capacity[]')[i]) if request.form.getlist('battery_capacity[]')[i] else None,
                        battery_type=request.form.getlist('battery_type[]')[i],
                        no_of_cells_bank=int(request.form.getlist('no_of_cells_bank[]')[i]) if request.form.getlist('no_of_cells_bank[]')[i] else None,
                        date_of_installation=request.form.getlist('date_of_installation_battery[]')[i],
                        load_on_battery_bank=float(request.form.getlist('load_on_battery_bank[]')[i]) if request.form.getlist('load_on_battery_bank[]')[i] else None,
                        practical_backup_time=float(request.form.getlist('practical_backup_time[]')[i]) if request.form.getlist('practical_backup_time[]')[i] else None,
                        battery_installed_new_or_used=request.form.getlist('battery_installed_new_or_used[]')[i],
                        battery_moved_from=request.form.getlist('battery_moved_from[]')[i]
                    )
                    general.battery_banks.append(battery)

            # Update AC Unit Information
            general.ac_units = []
            locations = request.form.getlist('location_of_ac_unit[]')
            for i in range(len(locations)):
                if locations[i]:
                    ac = ACUnit(
                        location_of_ac_unit=locations[i],
                        working_status=f"working_status_ac_{i}" in request.form.getlist('working_status_ac[]'),
                        ac_make=request.form.getlist('ac_make[]')[i],
                        capacity_tons=float(request.form.getlist('capacity_tons[]')[i]) if request.form.getlist('capacity_tons[]')[i] else None,
                        type_of_ac=request.form.getlist('type_of_ac[]')[i],
                        mount_type=request.form.getlist('mount_type[]')[i],
                        date_of_installation=request.form.getlist('date_of_installation_ac[]')[i],
                        sequence_controller_installed=f"sequence_controller_installed_{i}" in request.form.getlist('sequence_controller_installed[]'),
                        ac_load=float(request.form.getlist('ac_load[]')[i]) if request.form.getlist('ac_load[]')[i] else None,
                        total_ac_load=float(request.form.getlist('total_ac_load[]')[i]) if request.form.getlist('total_ac_load[]')[i] else None,
                        fault_nature_of_ac_unit=request.form.getlist('fault_nature_of_ac_unit[]')[i],
                        estimate_to_repair_ac=float(request.form.getlist('estimate_to_repair_ac[]')[i]) if request.form.getlist('estimate_to_repair_ac[]')[i] else None
                    )
                    general.ac_units.append(ac)

            # Update Solar Information
            if not general.solar_info:
                general.solar_info = SolarInformation()
            general.solar_info.total_solar_size = float(request.form['total_solar_size']) if request.form['total_solar_size'] else None
            general.solar_info.pv_solar_panel_capacity = float(request.form['pv_solar_panel_capacity']) if request.form['pv_solar_panel_capacity'] else None
            general.solar_info.no_of_pv_panels_installed = int(request.form['no_of_pv_panels_installed']) if request.form['no_of_pv_panels_installed'] else None
            general.solar_info.make_of_pv_panels = request.form['make_of_pv_panels']
            general.solar_info.charge_controller_make = request.form['charge_controller_make']

            db.session.commit()
            flash('Exchange updated successfully!')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating exchange: {str(e)}')
            return redirect(url_for('edit', sn=sn))
    return render_template('form.html', general=general, username=session.get('username', 'User'))

@app.route('/export')
@login_required
def export():
    try:
        user_region = session.get('region')
        if user_region == "All":
            exchanges = GeneralInformation.query.all()
        else:
            exchanges = GeneralInformation.query.filter_by(region=user_region).all()

        data = []
        for exchange in exchanges:
            row = {
                'SN': exchange.sn,
                'Region': exchange.region,
                'Domain': exchange.domain,
                'Exchange Name': exchange.exchange_name,
                'Exchange LIC': exchange.exchange_lic,
                'FLC': exchange.flc,
                'Site Category': exchange.site_category,
                'NEs Installed': exchange.nes_installed,
                'Latitude': exchange.latitude,
                'Longitude': exchange.longitude,
                'Tower Available': exchange.tower_available
            }

            # Tower Information
            for i, tower in enumerate(exchange.towers, 1):
                row[f'Tower {i} Type/Height'] = tower.tower_type_height

            # Power Information
            if exchange.power_info:
                row.update({
                    'WAPDA Ref Number': exchange.power_info.wapda_ref_number,
                    'Transformer Capacity': exchange.power_info.transformer_capacity,
                    'Transformer Earthing': exchange.power_info.transformer_earthing,
                    'Make of Rectifier': exchange.power_info.make_of_rectifier,
                    'Working Status (Power)': exchange.power_info.working_status,
                    'Rectifier Capacity': exchange.power_info.rectifier_capacity,
                    'No of Modules': exchange.power_info.no_of_modules,
                    'Capacity of Each Module': exchange.power_info.capacity_of_each_module,
                    'Working Modules': exchange.power_info.working_modules,
                    'Faulty Modules': exchange.power_info.faulty_modules,
                    'Space for New Modules': exchange.power_info.space_for_new_modules,
                    'Name of NEs Connected': exchange.power_info.name_of_nes_connected,
                    'Load of Individual NE': exchange.power_info.load_of_individual_ne,
                    'Grounding of Rectifier': exchange.power_info.grounding_of_rectifier,
                    'SPD in Rectifier': exchange.power_info.spd_in_rectifier,
                    'SPD Model': exchange.power_info.spd_model,
                    'Total Installed SPDs': exchange.power_info.total_installed_spds,
                    'No of Faulty SPDs': exchange.power_info.no_of_faulty_spds
                })

            # DG Information
            for i, dg in enumerate(exchange.dgs, 1):
                row.update({
                    f'DG {i} Installed DG': dg.installed_dg,
                    f'DG {i} Engine Make': dg.engine_make,
                    f'DG {i} Installation Year': dg.installation_year,
                    f'DG {i} DG Status': dg.dg_status,
                    f'DG {i} DG Starting Battery': dg.dg_starting_battery,
                    f'DG {i} Smart Switch Installed': dg.smart_switch_installed,
                    f'DG {i} ATS Installed': dg.ats_installed,
                    f'DG {i} ATS Capacity': dg.ats_capacity,
                    f'DG {i} Name of Faulty ATS Parts': dg.name_of_faulty_ats_parts,
                    f'DG {i} No of Faulty ATS Parts': dg.no_of_faulty_ats_parts,
                    f'DG {i} Load on DG P1': dg.load_on_dg_p1,
                    f'DG {i} Load on DG P2': dg.load_on_dg_p2,
                    f'DG {i} Load on DG P3': dg.load_on_dg_p3,
                    f'DG {i} Site Load Total': dg.site_load_total,
                    f'DG {i} Site Load P1': dg.site_load_p1,
                    f'DG {i} Site Load P2': dg.site_load_p2,
                    f'DG {i} Site Load P3': dg.site_load_p3
                })

            # Battery Bank Information
            for i, battery in enumerate(exchange.battery_banks, 1):
                row.update({
                    f'Battery {i} Make of Battery': battery.make_of_battery,
                    f'Battery {i} Battery Capacity': battery.battery_capacity,
                    f'Battery {i} Battery Type': battery.battery_type,
                    f'Battery {i} No of Cells/Bank': battery.no_of_cells_bank,
                    f'Battery {i} Date of Installation': battery.date_of_installation,
                    f'Battery {i} Load on Battery Bank': battery.load_on_battery_bank,
                    f'Battery {i} Practical Backup Time': battery.practical_backup_time,
                    f'Battery {i} Battery Installed (New/Used)': battery.battery_installed_new_or_used,
                    f'Battery {i} Battery Moved From': battery.battery_moved_from
                })

            # AC Unit Information
            for i, ac in enumerate(exchange.ac_units, 1):
                row.update({
                    f'AC Unit {i} Location': ac.location_of_ac_unit,
                    f'AC Unit {i} Working Status': ac.working_status,
                    f'AC Unit {i} AC Make': ac.ac_make,
                    f'AC Unit {i} Capacity (Tons)': ac.capacity_tons,
                    f'AC Unit {i} Type of AC': ac.type_of_ac,
                    f'AC Unit {i} Mount Type': ac.mount_type,
                    f'AC Unit {i} Date of Installation': ac.date_of_installation,
                    f'AC Unit {i} Sequence Controller Installed': ac.sequence_controller_installed,
                    f'AC Unit {i} AC Load': ac.ac_load,
                    f'AC Unit {i} Total AC Load': ac.total_ac_load,
                    f'AC Unit {i} Fault Nature of AC Unit': ac.fault_nature_of_ac_unit,
                    f'AC Unit {i} Estimate to Repair AC': ac.estimate_to_repair_ac
                })

            # Solar Information
            if exchange.solar_info:
                row.update({
                    'Total Solar Size': exchange.solar_info.total_solar_size,
                    'PV Solar Panel Capacity': exchange.solar_info.pv_solar_panel_capacity,
                    'No of PV Panels Installed': exchange.solar_info.no_of_pv_panels_installed,
                    'Make of PV Panels': exchange.solar_info.make_of_pv_panels,
                    'Charge Controller Make': exchange.solar_info.charge_controller_make
                })

            data.append(row)

        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Exchanges')
        output.seek(0)
        return send_file(
            output,
            download_name='exchanges.xlsx',
            as_attachment=True,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        flash(f'Error exporting data: {str(e)}')
        return redirect(url_for('index'))

@app.route('/view_exchanges')
@login_required
def view_exchanges():
    user_region = session.get('region')
    if user_region == "All":
        exchanges = GeneralInformation.query.all()
    else:
        exchanges = GeneralInformation.query.filter_by(region=user_region).all()
    return render_template('view_exchanges.html', exchanges=exchanges, username=session.get('username', 'User'))

if __name__ == '__main__':
    app.run(debug=True)