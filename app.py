import pandas as pd
import io
import os
from datetime import timedelta
from dotenv import load_dotenv
from supabase import create_client, Client
from functools import wraps
import secrets
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, make_response, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from html import escape
import logging
import traceback
from flask_wtf.csrf import generate_csrf

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['DEBUG'] = True  # Set to False in production
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

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Configure logging
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)

# Supabase setup
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Helper functions
def safe_float(value, field_name):
    try:
        return float(value) if value.strip() else None
    except ValueError:
        raise ValueError(f"Invalid numeric value for {field_name}: {value}")

def safe_int(value, field_name):
    try:
        return int(value) if value.strip() else None
    except ValueError:
        raise ValueError(f"Invalid integer value for {field_name}: {value}")

def sanitize_text(value):
    return escape(value.strip()) if value else None

# Define database models
class GeneralInformation(db.Model):
    sn = db.Column(db.Integer, primary_key=True)
    region = db.Column(db.String(50))
    domain = db.Column(db.String(50))
    site_name = db.Column(db.String(100))
    site_lic = db.Column(db.String(50))
    flc = db.Column(db.String(50))
    site_type = db.Column(db.String(50))
    site_category = db.Column(db.String(50))
    nes_installed = db.Column(db.Text)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    tower_available = db.Column(db.String(10))
    towers = db.relationship('Tower', backref='general_info', lazy=True, cascade="all, delete-orphan")
    power_info = db.relationship('PowerInformation', backref='general_info', uselist=False, cascade="all, delete-orphan")
    rectifiers = db.relationship('Rectifier', backref='general_info', lazy=True, cascade="all, delete-orphan")
    dgs = db.relationship('DGInformation', backref='general_info', lazy=True, cascade="all, delete-orphan")
    battery_banks = db.relationship('BatteryBank', backref='general_info', lazy=True, cascade="all, delete-orphan")
    ac_units = db.relationship('ACUnit', backref='general_info', lazy=True, cascade="all, delete-orphan")
    solar_info = db.relationship('SolarInformation', backref='general_info', uselist=False, cascade="all, delete-orphan")
    colocation_info = db.relationship('ColocationInformation', backref='general_info', uselist=False, cascade="all, delete-orphan")
    building_info = db.relationship('BuildingInformation', backref='general_info', uselist=False, cascade="all, delete-orphan")
    alarms = db.relationship('AlarmExtension', backref='general_info', lazy=True, cascade="all, delete-orphan")
    earthings = db.relationship('Earthing', backref='general_info', lazy=True, cascade="all, delete-orphan")
    fire_extinguishers = db.relationship('FireExtinguisher', backref='general_info', lazy=True, cascade="all, delete-orphan")
    pmr_infos = db.relationship('PMRInformation', backref='general_info', lazy=True, cascade="all, delete-orphan")

class Tower(db.Model):
    __tablename__ = 'tower'
    id = db.Column(db.Integer, primary_key=True)
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn', ondelete='CASCADE'))
    tower_type_height = db.Column(db.String(50))

class PowerInformation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn', ondelete='CASCADE'))
    wapda_ref_number = db.Column(db.String(50))
    transformer_capacity = db.Column(db.String(50))
    transformer_earthing = db.Column(db.String(10))  # Yes/No
    working_status = db.Column(db.String(20))  # Working/Faulty/Spare
    load_of_individual_ne = db.Column(db.Float, nullable=True)
    name_of_nes_connected = db.Column(db.Text)
    
class Rectifier(db.Model):
    __tablename__ = 'rectifier'
    id = db.Column(db.Integer, primary_key=True)
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn', ondelete='CASCADE'))
    make_of_rectifier = db.Column(db.String(50), nullable=True)
    rectifier_capacity = db.Column(db.Float, nullable=True)
    no_of_modules = db.Column(db.Integer, nullable=True)
    capacity_of_each_module = db.Column(db.Float, nullable=True)
    working_modules = db.Column(db.Integer, nullable=True)
    faulty_modules = db.Column(db.Integer, nullable=True)
    space_for_new_modules = db.Column(db.Integer, nullable=True)
    grounding_of_rectifier = db.Column(db.String(10), nullable=True)  # Yes/No
    spd_in_rectifier = db.Column(db.String(10), nullable=True)  # Yes/No
    spd_model = db.Column(db.String(50), nullable=True)
    total_installed_spds = db.Column(db.Integer, nullable=True)
    no_of_faulty_spds = db.Column(db.Integer, nullable=True)

class DGInformation(db.Model):
    __tablename__ = 'dg'
    id = db.Column(db.Integer, primary_key=True)
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn', ondelete='CASCADE'))
    installed_dg = db.Column(db.String(50))
    engine_make = db.Column(db.String(50))
    installation_year = db.Column(db.Integer, nullable=True)
    dg_status = db.Column(db.String(20))  # Working/Faulty/Spare
    dg_starting_battery = db.Column(db.String(50))
    smart_switch_installed = db.Column(db.String(10), nullable=True)  # Yes/No
    ats_installed = db.Column(db.String(10), nullable=True)  # Yes/No
    ats_capacity = db.Column(db.String(50))
    name_of_faulty_ats_parts = db.Column(db.String(100))
    no_of_faulty_ats_parts = db.Column(db.Integer, nullable=True)
    load_on_dg_p1 = db.Column(db.Float, nullable=True)
    load_on_dg_p2 = db.Column(db.Float, nullable=True)
    load_on_dg_p3 = db.Column(db.Float, nullable=True)
    site_load_total = db.Column(db.Float, nullable=True)
    site_load_p1 = db.Column(db.Float, nullable=True)
    site_load_p2 = db.Column(db.Float, nullable=True)
    site_load_p3 = db.Column(db.Float, nullable=True)

class BatteryBank(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn', ondelete='CASCADE'))
    make_of_battery = db.Column(db.String(50))
    battery_capacity = db.Column(db.Float, nullable=True)
    battery_type = db.Column(db.String(10))  # 2V/12V/48V
    no_of_cells_bank = db.Column(db.Integer, nullable=True)
    date_of_installation = db.Column(db.String(50))
    load_on_battery_bank = db.Column(db.Float, nullable=True)
    practical_backup_time = db.Column(db.Float, nullable=True)
    battery_installed_new_or_used = db.Column(db.String(20))  # New/Regenerated/Locally Arranged
    battery_moved_from = db.Column(db.String(100))

class ACUnit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn', ondelete='CASCADE'))
    location_of_ac_unit = db.Column(db.String(100))
    working_status = db.Column(db.String(20), nullable=True)  # Working/Faulty/Spare
    ac_make = db.Column(db.String(50))
    capacity_tons = db.Column(db.Float, nullable=True)
    type_of_ac = db.Column(db.String(50))
    mount_type = db.Column(db.String(50))
    date_of_installation = db.Column(db.String(50))
    sequence_controller_installed = db.Column(db.String(10), nullable=True)  # Yes/No
    ac_load = db.Column(db.Float, nullable=True)
    total_ac_load = db.Column(db.Float, nullable=True)
    fault_nature_of_ac_unit = db.Column(db.String(100))
    estimate_to_repair_ac = db.Column(db.Float, nullable=True)

class SolarInformation(db.Model):
    __tablename__ = 'installed_solar_information'
    id = db.Column(db.Integer, primary_key=True)
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn', ondelete='CASCADE'))
    total_solar_size = db.Column(db.Float, nullable=True)
    pv_solar_panel_capacity = db.Column(db.Float, nullable=True)
    no_of_pv_panels_installed = db.Column(db.Integer, nullable=True)
    make_of_pv_panels = db.Column(db.String(50))
    charge_controller_make = db.Column(db.String(50))

class ColocationInformation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn', ondelete='CASCADE'))
    colocation = db.Column(db.String(10), default='No')  # Yes/No
    name_of_colocation_vendors = db.Column(db.Text)
    load_of_each_vendor = db.Column(db.Float, nullable=True)
    total_load = db.Column(db.Float, nullable=True)

class BuildingInformation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn', ondelete='CASCADE'))
    building_status = db.Column(db.String(100))
    wall_doors_condition = db.Column(db.String(100))

class AlarmExtension(db.Model):
    __tablename__ = 'alarm_extension'
    id = db.Column(db.Integer, primary_key=True)
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn', ondelete='CASCADE'))
    ac_main_failure = db.Column(db.String(10), nullable=True)  # Yes/No
    dc_low_voltages = db.Column(db.String(10), nullable=True)  # Yes/No
    rectifier_failure = db.Column(db.String(10), nullable=True)  # Yes/No

class Earthing(db.Model):
    __tablename__ = 'earthing'
    id = db.Column(db.Integer, primary_key=True)
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn', ondelete='CASCADE'))
    earthing_value = db.Column(db.Float, nullable=True)
    no_of_pits = db.Column(db.Integer, nullable=True)

class FireExtinguisher(db.Model):
    __tablename__ = 'fire_extinguisher'
    id = db.Column(db.Integer, primary_key=True)
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn', ondelete='CASCADE'))
    fe_installed = db.Column(db.String(10), nullable=True)  # Yes/No
    no_of_fes = db.Column(db.Integer, nullable=True)
    type_of_gas = db.Column(db.String(50), nullable=True)
    date_of_expiry = db.Column(db.String(50), nullable=True)

class PMRInformation(db.Model):
    __tablename__ = 'pmr_information'
    id = db.Column(db.Integer, primary_key=True)
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn', ondelete='CASCADE'))
    pmr_performed = db.Column(db.String(10), nullable=True)  # Yes/No
    last_performed_date = db.Column(db.String(50), nullable=True)

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
                session['username'] = username
                resp = make_response(redirect(url_for('index')))
                resp.set_cookie('auth_token', access_token, httponly=True, secure=True, samesite='Lax')
                logging.info(f"User {username} logged in successfully")
                return resp
            else:
                error = response.error.message if hasattr(response, 'error') and response.error else 'Unknown error'
                flash(f'Login failed: {error}')
        except Exception as e:
            flash('Login failed: ' + str(e))
            logging.error(f"Login failed for {username}: {str(e)}")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    username = session.get('username')
    resp = make_response(redirect(url_for('login')))
    resp.set_cookie('auth_token', '', expires=0)
    session.pop('region', None)
    session.pop('username', None)
    supabase.auth.sign_out()
    logging.info(f"User {username} logged out")
    return resp

@app.route('/')
@login_required
def index():
    try:
        user_region = session.get('region')
        if user_region == "All":
            exchanges = GeneralInformation.query.all()
        else:
            exchanges = GeneralInformation.query.filter_by(domain=user_region).all()

        regions = db.session.query(GeneralInformation.domain, db.func.count(GeneralInformation.sn)).group_by(GeneralInformation.domain).all()
        region_labels = [r[0] for r in regions if r[0] is not None]
        region_counts = [r[1] for r in regions if r[0] is not None]

        total_exchanges = len(exchanges)
        year_counts = [total_exchanges // 2, total_exchanges - (total_exchanges // 2)]
        year_labels = ['2024', '2025']

        total_exchanges = len(exchanges)
        operational_exchanges = sum(1 for e in exchanges if e.power_info and e.power_info.working_status == 'Working')
        non_operational_exchanges = total_exchanges - operational_exchanges

        return render_template('index.html',
                             exchanges=exchanges,
                             region_labels=region_labels,
                             region_counts=region_counts,
                             year_labels=year_labels,
                             year_counts=year_counts,
                             total_exchanges=total_exchanges,
                             operational_exchanges=operational_exchanges,
                             non_operational_exchanges=non_operational_exchanges)
    except Exception as e:
        logging.error(f"Error in index route: {str(e)}")
        flash(f"Error: {str(e)}")
        return redirect(url_for('index'))

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        try:
            # General Information
            region = request.form.get('region')
            domain = request.form.get('domain')
            site_name = request.form.get('site_name')
            site_lic = request.form.get('site_lic') or None
            flc = request.form.get('flc') or None
            site_type = request.form.get('site_type')
            site_category = request.form.get('site_category')
            nes_installed = request.form.get('nes_installed') or None
            latitude = float(request.form.get('latitude')) if request.form.get('latitude') else None
            longitude = float(request.form.get('longitude')) if request.form.get('longitude') else None
            tower_available = request.form.get('tower_available')

            # Validate required fields
            if not all([domain, site_name, site_type, site_category]):
                raise ValueError("Missing required general information fields")

            # Calculate the next sn value
            max_sn = db.session.query(db.func.max(GeneralInformation.sn)).scalar() or 0
            new_sn = max_sn + 1

            # Create GeneralInformation instance with the new sn
            general = GeneralInformation(
                sn=new_sn,
                region=region,
                domain=domain,
                site_name=site_name,
                site_lic=site_lic,
                flc=flc,
                site_type=site_type,
                site_category=site_category,
                nes_installed=nes_installed,
                latitude=latitude,
                longitude=longitude,
                tower_available=tower_available,
            )

            # Add GeneralInformation to the session
            db.session.add(general)

            # Tower Information
            tower_types = request.form.getlist('tower_type_height[]')
            for tower_type in tower_types:
                if tower_type.strip():
                    tower = Tower(
                        general_id=general.sn,
                        tower_type_height=tower_type
                    )
                    db.session.add(tower)

            # Power Information
            power_info = PowerInformation(
                general_id=general.sn,
                wapda_ref_number=request.form.get('wapda_ref_number') or None,
                transformer_capacity=request.form.get('transformer_capacity') or None,
                transformer_earthing=request.form.get('transformer_earthing') or None,
                working_status=request.form.get('working_status_power') or None,
                name_of_nes_connected=request.form.get('name_of_nes_connected') or None,
                load_of_individual_ne=float(request.form.get('load_of_individual_ne')) if request.form.get('load_of_individual_ne') else None
            )
            db.session.add(power_info)

            # Rectifiers (Now using the new Rectifier model)
            make_of_rectifiers = request.form.getlist('make_of_rectifier[]')
            if make_of_rectifiers and make_of_rectifiers[0].strip():
                rectifier_capacities = request.form.getlist('rectifier_capacity[]')
                no_of_modules = request.form.getlist('no_of_modules[]')
                capacity_of_each_module = request.form.getlist('capacity_of_each_module[]')
                working_modules = request.form.getlist('working_modules[]')
                faulty_modules = request.form.getlist('faulty_modules[]')
                space_for_new_modules = request.form.getlist('space_for_new_modules[]')
                grounding_of_rectifiers = request.form.getlist('grounding_of_rectifier[]')
                spd_in_rectifiers = request.form.getlist('spd_in_rectifier[]')
                spd_models = request.form.getlist('spd_model[]')
                total_installed_spds = request.form.getlist('total_installed_spds[]')
                no_of_faulty_spds = request.form.getlist('no_of_faulty_spds[]')

                valid_yes_no = ['Yes', 'No']
                for i in range(len(make_of_rectifiers)):
                    if not make_of_rectifiers[i].strip():
                        continue
                    grounding = grounding_of_rectifiers[i] if grounding_of_rectifiers[i] in valid_yes_no else None
                    spd = spd_in_rectifiers[i] if spd_in_rectifiers[i] in valid_yes_no else None
                    rectifier = Rectifier(
                        general_id=general.sn,
                        make_of_rectifier=make_of_rectifiers[i] or None,
                        rectifier_capacity=float(rectifier_capacities[i]) if rectifier_capacities[i].strip() else None,
                        no_of_modules=int(no_of_modules[i]) if no_of_modules[i].strip() else None,
                        capacity_of_each_module=float(capacity_of_each_module[i]) if capacity_of_each_module[i].strip() else None,
                        working_modules=int(working_modules[i]) if working_modules[i].strip() else None,
                        faulty_modules=int(faulty_modules[i]) if faulty_modules[i].strip() else None,
                        space_for_new_modules=int(space_for_new_modules[i]) if space_for_new_modules[i].strip() else None,
                        grounding_of_rectifier=grounding,
                        spd_in_rectifier=spd,
                        spd_model=spd_models[i] if spd_models[i].strip() else None,
                        total_installed_spds=int(total_installed_spds[i]) if total_installed_spds[i].strip() else None,
                        no_of_faulty_spds=int(no_of_faulty_spds[i]) if no_of_faulty_spds[i].strip() else None
                    )
                    db.session.add(rectifier)

            # DG Information
            installed_dgs = request.form.getlist('installed_dg[]')
            if installed_dgs and installed_dgs[0].strip():
                engine_makes = request.form.getlist('engine_make[]')
                installation_years = request.form.getlist('installation_year[]')
                dg_statuses = request.form.getlist('dg_status[]')
                dg_starting_batteries = request.form.getlist('dg_starting_battery[]')
                smart_switch_installeds = request.form.getlist('smart_switch_installed[]')
                ats_installeds = request.form.getlist('ats_installed[]')
                ats_capacities = request.form.getlist('ats_capacity[]')
                name_of_faulty_ats_parts = request.form.getlist('name_of_faulty_ats_parts[]')
                no_of_faulty_ats_parts = request.form.getlist('no_of_faulty_ats_parts[]')
                load_on_dg_p1s = request.form.getlist('load_on_dg_p1[]')
                load_on_dg_p2s = request.form.getlist('load_on_dg_p2[]')
                load_on_dg_p3s = request.form.getlist('load_on_dg_p3[]')
                site_load_totals = request.form.getlist('site_load_total[]')
                site_load_p1s = request.form.getlist('site_load_p1[]')
                site_load_p2s = request.form.getlist('site_load_p2[]')
                site_load_p3s = request.form.getlist('site_load_p3[]')

                valid_dg_status = ['Working', 'Faulty', 'Spare']
                for i in range(len(installed_dgs)):
                    if not installed_dgs[i].strip():
                        continue
                    dg_status = dg_statuses[i] if dg_statuses[i] in valid_dg_status else None
                    smart_switch = smart_switch_installeds[i] if smart_switch_installeds[i] in valid_yes_no else None
                    ats = ats_installeds[i] if ats_installeds[i] in valid_yes_no else None
                    dg = DGInformation(
                        general_id=general.sn,
                        installed_dg=installed_dgs[i] or None,
                        engine_make=engine_makes[i] if engine_makes[i].strip() else None,
                        installation_year=int(installation_years[i]) if installation_years[i].strip() else None,
                        dg_status=dg_status,
                        dg_starting_battery=dg_starting_batteries[i] if dg_starting_batteries[i].strip() else None,
                        smart_switch_installed=smart_switch,
                        ats_installed=ats,
                        ats_capacity=ats_capacities[i] if ats_capacities[i].strip() else None,
                        name_of_faulty_ats_parts=name_of_faulty_ats_parts[i] if name_of_faulty_ats_parts[i].strip() else None,
                        no_of_faulty_ats_parts=int(no_of_faulty_ats_parts[i]) if no_of_faulty_ats_parts[i].strip() else None,
                        load_on_dg_p1=float(load_on_dg_p1s[i]) if load_on_dg_p1s[i].strip() else None,
                        load_on_dg_p2=float(load_on_dg_p2s[i]) if load_on_dg_p2s[i].strip() else None,
                        load_on_dg_p3=float(load_on_dg_p3s[i]) if load_on_dg_p3s[i].strip() else None,
                        site_load_total=float(site_load_totals[i]) if site_load_totals[i].strip() else None,
                        site_load_p1=float(site_load_p1s[i]) if site_load_p1s[i].strip() else None,
                        site_load_p2=float(site_load_p2s[i]) if site_load_p2s[i].strip() else None,
                        site_load_p3=float(site_load_p3s[i]) if site_load_p3s[i].strip() else None
                    )
                    db.session.add(dg)

            # Battery Bank Information
            make_of_batteries = request.form.getlist('make_of_battery[]')
            if make_of_batteries and make_of_batteries[0].strip():
                battery_capacities = request.form.getlist('battery_capacity[]')
                battery_types = request.form.getlist('battery_type[]')
                no_of_cells_banks = request.form.getlist('no_of_cells_bank[]')
                date_of_installations = request.form.getlist('date_of_installation_battery[]')
                load_on_battery_banks = request.form.getlist('load_on_battery_bank[]')
                practical_backup_times = request.form.getlist('practical_backup_time[]')
                battery_installed_new_or_useds = request.form.getlist('battery_installed_new_or_used[]')
                battery_moved_froms = request.form.getlist('battery_moved_from[]')

                valid_battery_types = ['2V', '12V', '48V']
                valid_battery_installation = ['New', 'Regenerated', 'Locally Arranged']
                for i in range(len(make_of_batteries)):
                    if not make_of_batteries[i].strip():
                        continue
                    battery_type = battery_types[i] if battery_types[i] in valid_battery_types else None
                    battery_installation = battery_installed_new_or_useds[i] if battery_installed_new_or_useds[i] in valid_battery_installation else None
                    battery = BatteryBank(
                        general_id=general.sn,
                        make_of_battery=make_of_batteries[i] or None,
                        battery_capacity=float(battery_capacities[i]) if battery_capacities[i].strip() else None,
                        battery_type=battery_type,
                        no_of_cells_bank=int(no_of_cells_banks[i]) if no_of_cells_banks[i].strip() else None,
                        date_of_installation=date_of_installations[i] if date_of_installations[i].strip() else None,
                        load_on_battery_bank=float(load_on_battery_banks[i]) if load_on_battery_banks[i].strip() else None,
                        practical_backup_time=float(practical_backup_times[i]) if practical_backup_times[i].strip() else None,
                        battery_installed_new_or_used=battery_installation,
                        battery_moved_from=battery_moved_froms[i] if battery_moved_froms[i].strip() else None
                    )
                    db.session.add(battery)

            # AC Unit Information
            location_of_ac_units = request.form.getlist('location_of_ac_unit[]')
            if location_of_ac_units and location_of_ac_units[0].strip():
                working_status_acs = request.form.getlist('working_status_ac[]')
                ac_makes = request.form.getlist('ac_make[]')
                capacity_tons = request.form.getlist('capacity_tons[]')
                type_of_acs = request.form.getlist('type_of_ac[]')
                mount_types = request.form.getlist('mount_type[]')
                date_of_installation_acs = request.form.getlist('date_of_installation_ac[]')
                sequence_controller_installeds = request.form.getlist('sequence_controller_installed[]')
                ac_loads = request.form.getlist('ac_load[]')
                total_ac_loads = request.form.getlist('total_ac_load[]')
                fault_nature_of_ac_units = request.form.getlist('fault_nature_of_ac_unit[]')
                estimate_to_repair_acs = request.form.getlist('estimate_to_repair_ac[]')

                valid_working_status = ['Working', 'Faulty', 'Spare']
                for i in range(len(location_of_ac_units)):
                    if not location_of_ac_units[i].strip():
                        continue
                    working_status = working_status_acs[i] if working_status_acs[i] in valid_working_status else None
                    sequence_controller = sequence_controller_installeds[i] if sequence_controller_installeds[i] in valid_yes_no else None
                    ac_unit = ACUnit(
                        general_id=general.sn,
                        location_of_ac_unit=location_of_ac_units[i] or None,
                        working_status=working_status,
                        ac_make=ac_makes[i] if ac_makes[i].strip() else None,
                        capacity_tons=float(capacity_tons[i]) if capacity_tons[i].strip() else None,
                        type_of_ac=type_of_acs[i] if type_of_acs[i].strip() else None,
                        mount_type=mount_types[i] if mount_types[i].strip() else None,
                        date_of_installation=date_of_installation_acs[i] if date_of_installation_acs[i].strip() else None,
                        sequence_controller_installed=sequence_controller,
                        ac_load=float(ac_loads[i]) if ac_loads[i].strip() else None,
                        total_ac_load=float(total_ac_loads[i]) if total_ac_loads[i].strip() else None,
                        fault_nature_of_ac_unit=fault_nature_of_ac_units[i] if fault_nature_of_ac_units[i].strip() else None,
                        estimate_to_repair_ac=float(estimate_to_repair_acs[i]) if estimate_to_repair_acs[i].strip() else None
                    )
                    db.session.add(ac_unit)

            # Solar Information
            solar_info = SolarInformation(
                general_id=general.sn,
                total_solar_size=float(request.form.get('total_solar_size')) if request.form.get('total_solar_size') else None,
                pv_solar_panel_capacity=float(request.form.get('pv_solar_panel_capacity')) if request.form.get('pv_solar_panel_capacity') else None,
                no_of_pv_panels_installed=int(request.form.get('no_of_pv_panels_installed')) if request.form.get('no_of_pv_panels_installed') else None,
                make_of_pv_panels=request.form.get('make_of_pv_panels') or None,
                charge_controller_make=request.form.get('charge_controller_make') or None
            )
            db.session.add(solar_info)

            # Colocation Information
            colocation = request.form.get('colocation')
            colocation_info = ColocationInformation(
                general_id=general.sn,
                colocation=colocation,
                name_of_colocation_vendors=request.form.get('name_of_colocation_vendors') or None,
                load_of_each_vendor=float(request.form.get('load_of_each_vendor')) if request.form.get('load_of_each_vendor') else None,
                total_load=float(request.form.get('total_load')) if request.form.get('total_load') else None
            )
            db.session.add(colocation_info)

            # Building Information
            building_info = BuildingInformation(
                general_id=general.sn,
                building_status=request.form.get('building_status') or None,
                wall_doors_condition=request.form.get('wall_doors_condition') or None
            )
            db.session.add(building_info)

            # Alarm Extension
            ac_main_failures = request.form.getlist('ac_main_failure[]')
            if ac_main_failures and ac_main_failures[0].strip():
                dc_low_voltages = request.form.getlist('dc_low_voltages[]')
                rectifier_failures = request.form.getlist('rectifier_failure[]')
                for i in range(len(ac_main_failures)):
                    if not ac_main_failures[i].strip():
                        continue
                    ac_main_failure = ac_main_failures[i] if ac_main_failures[i] in valid_yes_no else None
                    dc_low_voltage = dc_low_voltages[i] if dc_low_voltages[i] in valid_yes_no else None
                    rectifier_failure = rectifier_failures[i] if rectifier_failures[i] in valid_yes_no else None
                    alarm = AlarmExtension(
                        general_id=general.sn,
                        ac_main_failure=ac_main_failure,
                        dc_low_voltages=dc_low_voltage,
                        rectifier_failure=rectifier_failure
                    )
                    db.session.add(alarm)

            # Earthing
            earthing_values = request.form.getlist('earthing_value[]')
            if earthing_values and earthing_values[0].strip():
                no_of_pits = request.form.getlist('no_of_pits[]')
                for i in range(len(earthing_values)):
                    if not earthing_values[i].strip():
                        continue
                    earthing = Earthing(
                        general_id=general.sn,
                        earthing_value=float(earthing_values[i]) if earthing_values[i].strip() else None,
                        no_of_pits=int(no_of_pits[i]) if no_of_pits[i].strip() else None
                    )
                    db.session.add(earthing)

            # Fire Extinguishers
            fe_installeds = request.form.getlist('fe_installed[]')
            if fe_installeds and fe_installeds[0].strip():
                no_of_fes = request.form.getlist('no_of_fes[]')
                type_of_gases = request.form.getlist('type_of_gas[]')
                date_of_expiries = request.form.getlist('date_of_expiry[]')
                for i in range(len(fe_installeds)):
                    if not fe_installeds[i].strip():
                        continue
                    fe_installed = fe_installeds[i] if fe_installeds[i] in valid_yes_no else None
                    fire_ext = FireExtinguisher(
                        general_id=general.sn,
                        fe_installed=fe_installed,
                        no_of_fes=int(no_of_fes[i]) if no_of_fes[i].strip() else None,
                        type_of_gas=type_of_gases[i] if type_of_gases[i].strip() else None,
                        date_of_expiry=date_of_expiries[i] if date_of_expiries[i].strip() else None
                    )
                    db.session.add(fire_ext)

            # PMR Information
            pmr_performeds = request.form.getlist('pmr_performed[]')
            if pmr_performeds and pmr_performeds[0].strip():
                last_performed_dates = request.form.getlist('last_performed_date[]')
                for i in range(len(pmr_performeds)):
                    if not pmr_performeds[i].strip():
                        continue
                    pmr_performed = pmr_performeds[i] if pmr_performeds[i] in valid_yes_no else None
                    pmr = PMRInformation(
                        general_id=general.sn,
                        pmr_performed=pmr_performed,
                        last_performed_date=last_performed_dates[i] if last_performed_dates[i].strip() else None
                    )
                    db.session.add(pmr)

            # Final commit for all related objects
            db.session.commit()

            flash('Exchange added successfully!', 'success')
            return redirect(url_for('index'))

        except ValueError as e:
            db.session.rollback()
            flash(str(e), 'error')
        except Exception as e:
            db.session.rollback()
            error_msg = f"Error adding exchange: {str(e)}\nTraceback: {traceback.format_exc()}"
            flash(error_msg, 'error')
            logging.error(error_msg)

    return render_template('add.html', general=None)
    
@app.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        try:
            # General Information
            region = request.form.get('region')
            domain = request.form.get('domain')
            site_name = request.form.get('site_name')
            site_lic = request.form.get('site_lic') or None
            flc = request.form.get('flc') or None
            site_type = request.form.get('site_type')
            site_category = request.form.get('site_category')
            nes_installed = request.form.get('nes_installed') or None
            latitude = float(request.form.get('latitude')) if request.form.get('latitude') else None
            longitude = float(request.form.get('longitude')) if request.form.get('longitude') else None
            tower_available = request.form.get('tower_available')

            # Validate required fields
            if not all([domain, site_name, site_type, site_category]):
                raise ValueError("Missing required general information fields")

            # Calculate the next sn value
            max_sn = db.session.query(db.func.max(GeneralInformation.sn)).scalar() or 0
            new_sn = max_sn + 1

            # Create GeneralInformation instance with the new sn
            general = GeneralInformation(
                sn=new_sn,
                region=region,
                domain=domain,
                site_name=site_name,
                site_lic=site_lic,
                flc=flc,
                site_type=site_type,
                site_category=site_category,
                nes_installed=nes_installed,
                latitude=latitude,
                longitude=longitude,
                tower_available=tower_available,
            )

            # Add GeneralInformation to the session
            db.session.add(general)

            # Tower Information
            tower_types = request.form.getlist('tower_type_height[]')
            for tower_type in tower_types:
                if tower_type.strip():
                    tower = Tower(
                        general_id=general.sn,
                        tower_type_height=tower_type
                    )
                    db.session.add(tower)

            # Power Information
            power_info = PowerInformation(
                general_id=general.sn,
                wapda_ref_number=request.form.get('wapda_ref_number') or None,
                transformer_capacity=request.form.get('transformer_capacity') or None,
                transformer_earthing=request.form.get('transformer_earthing') or None,
                working_status=request.form.get('working_status_power') or None,
                name_of_nes_connected=request.form.get('name_of_nes_connected') or None,
                load_of_individual_ne=float(request.form.get('load_of_individual_ne')) if request.form.get('load_of_individual_ne') else None
            )
            db.session.add(power_info)

            # Rectifiers (Now using the new Rectifier model)
            make_of_rectifiers = request.form.getlist('make_of_rectifier[]')
            if make_of_rectifiers and make_of_rectifiers[0].strip():
                rectifier_capacities = request.form.getlist('rectifier_capacity[]')
                no_of_modules = request.form.getlist('no_of_modules[]')
                capacity_of_each_module = request.form.getlist('capacity_of_each_module[]')
                working_modules = request.form.getlist('working_modules[]')
                faulty_modules = request.form.getlist('faulty_modules[]')
                space_for_new_modules = request.form.getlist('space_for_new_modules[]')
                grounding_of_rectifiers = request.form.getlist('grounding_of_rectifier[]')
                spd_in_rectifiers = request.form.getlist('spd_in_rectifier[]')
                spd_models = request.form.getlist('spd_model[]')
                total_installed_spds = request.form.getlist('total_installed_spds[]')
                no_of_faulty_spds = request.form.getlist('no_of_faulty_spds[]')

                valid_yes_no = ['Yes', 'No']
                for i in range(len(make_of_rectifiers)):
                    if not make_of_rectifiers[i].strip():
                        continue
                    grounding = grounding_of_rectifiers[i] if grounding_of_rectifiers[i] in valid_yes_no else None
                    spd = spd_in_rectifiers[i] if spd_in_rectifiers[i] in valid_yes_no else None
                    rectifier = Rectifier(
                        general_id=general.sn,
                        make_of_rectifier=make_of_rectifiers[i] or None,
                        rectifier_capacity=float(rectifier_capacities[i]) if rectifier_capacities[i].strip() else None,
                        no_of_modules=int(no_of_modules[i]) if no_of_modules[i].strip() else None,
                        capacity_of_each_module=float(capacity_of_each_module[i]) if capacity_of_each_module[i].strip() else None,
                        working_modules=int(working_modules[i]) if working_modules[i].strip() else None,
                        faulty_modules=int(faulty_modules[i]) if faulty_modules[i].strip() else None,
                        space_for_new_modules=int(space_for_new_modules[i]) if space_for_new_modules[i].strip() else None,
                        grounding_of_rectifier=grounding,
                        spd_in_rectifier=spd,
                        spd_model=spd_models[i] if spd_models[i].strip() else None,
                        total_installed_spds=int(total_installed_spds[i]) if total_installed_spds[i].strip() else None,
                        no_of_faulty_spds=int(no_of_faulty_spds[i]) if no_of_faulty_spds[i].strip() else None
                    )
                    db.session.add(rectifier)

            # DG Information
            installed_dgs = request.form.getlist('installed_dg[]')
            if installed_dgs and installed_dgs[0].strip():
                engine_makes = request.form.getlist('engine_make[]')
                installation_years = request.form.getlist('installation_year[]')
                dg_statuses = request.form.getlist('dg_status[]')
                dg_starting_batteries = request.form.getlist('dg_starting_battery[]')
                smart_switch_installeds = request.form.getlist('smart_switch_installed[]')
                ats_installeds = request.form.getlist('ats_installed[]')
                ats_capacities = request.form.getlist('ats_capacity[]')
                name_of_faulty_ats_parts = request.form.getlist('name_of_faulty_ats_parts[]')
                no_of_faulty_ats_parts = request.form.getlist('no_of_faulty_ats_parts[]')
                load_on_dg_p1s = request.form.getlist('load_on_dg_p1[]')
                load_on_dg_p2s = request.form.getlist('load_on_dg_p2[]')
                load_on_dg_p3s = request.form.getlist('load_on_dg_p3[]')
                site_load_totals = request.form.getlist('site_load_total[]')
                site_load_p1s = request.form.getlist('site_load_p1[]')
                site_load_p2s = request.form.getlist('site_load_p2[]')
                site_load_p3s = request.form.getlist('site_load_p3[]')

                valid_dg_status = ['Working', 'Faulty', 'Spare']
                for i in range(len(installed_dgs)):
                    if not installed_dgs[i].strip():
                        continue
                    dg_status = dg_statuses[i] if dg_statuses[i] in valid_dg_status else None
                    smart_switch = smart_switch_installeds[i] if smart_switch_installeds[i] in valid_yes_no else None
                    ats = ats_installeds[i] if ats_installeds[i] in valid_yes_no else None
                    dg = DGInformation(
                        general_id=general.sn,
                        installed_dg=installed_dgs[i] or None,
                        engine_make=engine_makes[i] if engine_makes[i].strip() else None,
                        installation_year=int(installation_years[i]) if installation_years[i].strip() else None,
                        dg_status=dg_status,
                        dg_starting_battery=dg_starting_batteries[i] if dg_starting_batteries[i].strip() else None,
                        smart_switch_installed=smart_switch,
                        ats_installed=ats,
                        ats_capacity=ats_capacities[i] if ats_capacities[i].strip() else None,
                        name_of_faulty_ats_parts=name_of_faulty_ats_parts[i] if name_of_faulty_ats_parts[i].strip() else None,
                        no_of_faulty_ats_parts=int(no_of_faulty_ats_parts[i]) if no_of_faulty_ats_parts[i].strip() else None,
                        load_on_dg_p1=float(load_on_dg_p1s[i]) if load_on_dg_p1s[i].strip() else None,
                        load_on_dg_p2=float(load_on_dg_p2s[i]) if load_on_dg_p2s[i].strip() else None,
                        load_on_dg_p3=float(load_on_dg_p3s[i]) if load_on_dg_p3s[i].strip() else None,
                        site_load_total=float(site_load_totals[i]) if site_load_totals[i].strip() else None,
                        site_load_p1=float(site_load_p1s[i]) if site_load_p1s[i].strip() else None,
                        site_load_p2=float(site_load_p2s[i]) if site_load_p2s[i].strip() else None,
                        site_load_p3=float(site_load_p3s[i]) if site_load_p3s[i].strip() else None
                    )
                    db.session.add(dg)

            # Battery Bank Information
            make_of_batteries = request.form.getlist('make_of_battery[]')
            if make_of_batteries and make_of_batteries[0].strip():
                battery_capacities = request.form.getlist('battery_capacity[]')
                battery_types = request.form.getlist('battery_type[]')
                no_of_cells_banks = request.form.getlist('no_of_cells_bank[]')
                date_of_installations = request.form.getlist('date_of_installation_battery[]')
                load_on_battery_banks = request.form.getlist('load_on_battery_bank[]')
                practical_backup_times = request.form.getlist('practical_backup_time[]')
                battery_installed_new_or_useds = request.form.getlist('battery_installed_new_or_used[]')
                battery_moved_froms = request.form.getlist('battery_moved_from[]')

                valid_battery_types = ['2V', '12V', '48V']
                valid_battery_installation = ['New', 'Regenerated', 'Locally Arranged']
                for i in range(len(make_of_batteries)):
                    if not make_of_batteries[i].strip():
                        continue
                    battery_type = battery_types[i] if battery_types[i] in valid_battery_types else None
                    battery_installation = battery_installed_new_or_useds[i] if battery_installed_new_or_useds[i] in valid_battery_installation else None
                    battery = BatteryBank(
                        general_id=general.sn,
                        make_of_battery=make_of_batteries[i] or None,
                        battery_capacity=float(battery_capacities[i]) if battery_capacities[i].strip() else None,
                        battery_type=battery_type,
                        no_of_cells_bank=int(no_of_cells_banks[i]) if no_of_cells_banks[i].strip() else None,
                        date_of_installation=date_of_installations[i] if date_of_installations[i].strip() else None,
                        load_on_battery_bank=float(load_on_battery_banks[i]) if load_on_battery_banks[i].strip() else None,
                        practical_backup_time=float(practical_backup_times[i]) if practical_backup_times[i].strip() else None,
                        battery_installed_new_or_used=battery_installation,
                        battery_moved_from=battery_moved_froms[i] if battery_moved_froms[i].strip() else None
                    )
                    db.session.add(battery)

            # AC Unit Information
            location_of_ac_units = request.form.getlist('location_of_ac_unit[]')
            if location_of_ac_units and location_of_ac_units[0].strip():
                working_status_acs = request.form.getlist('working_status_ac[]')
                ac_makes = request.form.getlist('ac_make[]')
                capacity_tons = request.form.getlist('capacity_tons[]')
                type_of_acs = request.form.getlist('type_of_ac[]')
                mount_types = request.form.getlist('mount_type[]')
                date_of_installation_acs = request.form.getlist('date_of_installation_ac[]')
                sequence_controller_installeds = request.form.getlist('sequence_controller_installed[]')
                ac_loads = request.form.getlist('ac_load[]')
                total_ac_loads = request.form.getlist('total_ac_load[]')
                fault_nature_of_ac_units = request.form.getlist('fault_nature_of_ac_unit[]')
                estimate_to_repair_acs = request.form.getlist('estimate_to_repair_ac[]')

                valid_working_status = ['Working', 'Faulty', 'Spare']
                for i in range(len(location_of_ac_units)):
                    if not location_of_ac_units[i].strip():
                        continue
                    working_status = working_status_acs[i] if working_status_acs[i] in valid_working_status else None
                    sequence_controller = sequence_controller_installeds[i] if sequence_controller_installeds[i] in valid_yes_no else None
                    ac_unit = ACUnit(
                        general_id=general.sn,
                        location_of_ac_unit=location_of_ac_units[i] or None,
                        working_status=working_status,
                        ac_make=ac_makes[i] if ac_makes[i].strip() else None,
                        capacity_tons=float(capacity_tons[i]) if capacity_tons[i].strip() else None,
                        type_of_ac=type_of_acs[i] if type_of_acs[i].strip() else None,
                        mount_type=mount_types[i] if mount_types[i].strip() else None,
                        date_of_installation=date_of_installation_acs[i] if date_of_installation_acs[i].strip() else None,
                        sequence_controller_installed=sequence_controller,
                        ac_load=float(ac_loads[i]) if ac_loads[i].strip() else None,
                        total_ac_load=float(total_ac_loads[i]) if total_ac_loads[i].strip() else None,
                        fault_nature_of_ac_unit=fault_nature_of_ac_units[i] if fault_nature_of_ac_units[i].strip() else None,
                        estimate_to_repair_ac=float(estimate_to_repair_acs[i]) if estimate_to_repair_acs[i].strip() else None
                    )
                    db.session.add(ac_unit)

            # Solar Information
            solar_info = SolarInformation(
                general_id=general.sn,
                total_solar_size=float(request.form.get('total_solar_size')) if request.form.get('total_solar_size') else None,
                pv_solar_panel_capacity=float(request.form.get('pv_solar_panel_capacity')) if request.form.get('pv_solar_panel_capacity') else None,
                no_of_pv_panels_installed=int(request.form.get('no_of_pv_panels_installed')) if request.form.get('no_of_pv_panels_installed') else None,
                make_of_pv_panels=request.form.get('make_of_pv_panels') or None,
                charge_controller_make=request.form.get('charge_controller_make') or None
            )
            db.session.add(solar_info)

            # Colocation Information
            colocation = request.form.get('colocation')
            colocation_info = ColocationInformation(
                general_id=general.sn,
                colocation=colocation,
                name_of_colocation_vendors=request.form.get('name_of_colocation_vendors') or None,
                load_of_each_vendor=float(request.form.get('load_of_each_vendor')) if request.form.get('load_of_each_vendor') else None,
                total_load=float(request.form.get('total_load')) if request.form.get('total_load') else None
            )
            db.session.add(colocation_info)

            # Building Information
            building_info = BuildingInformation(
                general_id=general.sn,
                building_status=request.form.get('building_status') or None,
                wall_doors_condition=request.form.get('wall_doors_condition') or None
            )
            db.session.add(building_info)

            # Alarm Extension
            ac_main_failures = request.form.getlist('ac_main_failure[]')
            if ac_main_failures and ac_main_failures[0].strip():
                dc_low_voltages = request.form.getlist('dc_low_voltages[]')
                rectifier_failures = request.form.getlist('rectifier_failure[]')
                for i in range(len(ac_main_failures)):
                    if not ac_main_failures[i].strip():
                        continue
                    ac_main_failure = ac_main_failures[i] if ac_main_failures[i] in valid_yes_no else None
                    dc_low_voltage = dc_low_voltages[i] if dc_low_voltages[i] in valid_yes_no else None
                    rectifier_failure = rectifier_failures[i] if rectifier_failures[i] in valid_yes_no else None
                    alarm = AlarmExtension(
                        general_id=general.sn,
                        ac_main_failure=ac_main_failure,
                        dc_low_voltages=dc_low_voltage,
                        rectifier_failure=rectifier_failure
                    )
                    db.session.add(alarm)

            # Earthing
            earthing_values = request.form.getlist('earthing_value[]')
            if earthing_values and earthing_values[0].strip():
                no_of_pits = request.form.getlist('no_of_pits[]')
                for i in range(len(earthing_values)):
                    if not earthing_values[i].strip():
                        continue
                    earthing = Earthing(
                        general_id=general.sn,
                        earthing_value=float(earthing_values[i]) if earthing_values[i].strip() else None,
                        no_of_pits=int(no_of_pits[i]) if no_of_pits[i].strip() else None
                    )
                    db.session.add(earthing)

            # Fire Extinguishers
            fe_installeds = request.form.getlist('fe_installed[]')
            if fe_installeds and fe_installeds[0].strip():
                no_of_fes = request.form.getlist('no_of_fes[]')
                type_of_gases = request.form.getlist('type_of_gas[]')
                date_of_expiries = request.form.getlist('date_of_expiry[]')
                for i in range(len(fe_installeds)):
                    if not fe_installeds[i].strip():
                        continue
                    fe_installed = fe_installeds[i] if fe_installeds[i] in valid_yes_no else None
                    fire_ext = FireExtinguisher(
                        general_id=general.sn,
                        fe_installed=fe_installed,
                        no_of_fes=int(no_of_fes[i]) if no_of_fes[i].strip() else None,
                        type_of_gas=type_of_gases[i] if type_of_gases[i].strip() else None,
                        date_of_expiry=date_of_expiries[i] if date_of_expiries[i].strip() else None
                    )
                    db.session.add(fire_ext)

            # PMR Information
            pmr_performeds = request.form.getlist('pmr_performed[]')
            if pmr_performeds and pmr_performeds[0].strip():
                last_performed_dates = request.form.getlist('last_performed_date[]')
                for i in range(len(pmr_performeds)):
                    if not pmr_performeds[i].strip():
                        continue
                    pmr_performed = pmr_performeds[i] if pmr_performeds[i] in valid_yes_no else None
                    pmr = PMRInformation(
                        general_id=general.sn,
                        pmr_performed=pmr_performed,
                        last_performed_date=last_performed_dates[i] if last_performed_dates[i].strip() else None
                    )
                    db.session.add(pmr)

            # Final commit for all related objects
            db.session.commit()

            flash('Exchange added successfully!', 'success')
            return redirect(url_for('index'))

        except ValueError as e:
            db.session.rollback()
            flash(str(e), 'error')
        except Exception as e:
            db.session.rollback()
            error_msg = f"Error adding exchange: {str(e)}\nTraceback: {traceback.format_exc()}"
            flash(error_msg, 'error')
            logging.error(error_msg)

    return render_template('add.html', general=general)

@app.route('/delete/<int:sn>', methods=['DELETE'])
@login_required
def delete(sn):
    if session.get('region') != 'All':
        return jsonify({'success': False, 'message': 'Unauthorized access'}), 403
    
    general = GeneralInformation.query.get_or_404(sn)
    try:
        logging.info(f"User {session.get('username')} deleted exchange SN {sn}")
        db.session.delete(general)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Exchange deleted successfully'})
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting exchange SN {sn} by {session.get('username')}: {str(e)}")
        return jsonify({'success': False, 'message': f'Error deleting exchange: {str(e)}'}), 500

@app.route('/export')
@login_required
def export():
    try:
        user_region = session.get('region')
        if user_region == "All":
            exchanges = GeneralInformation.query.limit(1000).all()
        else:
            exchanges = GeneralInformation.query.filter_by(domain=user_region).limit(1000).all()

        if not exchanges:
            flash('No exchanges found to export.')
            return redirect(url_for('index'))

        total_exchanges = GeneralInformation.query.count()
        if total_exchanges > 1000:
            flash('Export limited to 1000 records. Please contact support for a full export.')

        # Determine the maximum number of entries for each related model
        max_towers = max(len(exchange.towers) for exchange in exchanges) if exchanges else 0
        max_rectifiers = max(len(exchange.rectifiers) for exchange in exchanges) if exchanges else 0
        max_dgs = max(len(exchange.dgs) for exchange in exchanges) if exchanges else 0
        max_batteries = max(len(exchange.battery_banks) for exchange in exchanges) if exchanges else 0
        max_acs = max(len(exchange.ac_units) for exchange in exchanges) if exchanges else 0
        max_alarms = max(len(exchange.alarms) for exchange in exchanges) if exchanges else 0
        max_earthings = max(len(exchange.earthings) for exchange in exchanges) if exchanges else 0
        max_fire_extinguishers = max(len(exchange.fire_extinguishers) for exchange in exchanges) if exchanges else 0
        max_pmrs = max(len(exchange.pmr_infos) for exchange in exchanges) if exchanges else 0

        data = []
        for exchange in exchanges:
            row = {
                'SN': exchange.sn,
                'Region': exchange.region,
                'Domain': exchange.domain,
                'Site Name': exchange.site_name,
                'Site LIC': exchange.site_lic,
                'FLC': exchange.flc,
                'Site Category': exchange.site_category,
                'NEs Installed': exchange.nes_installed,
                'Latitude': exchange.latitude,
                'Longitude': exchange.longitude,
                'Tower Available': exchange.tower_available
            }

            # Handle Towers
            for i in range(max_towers):
                tower = exchange.towers[i] if i < len(exchange.towers) else None
                row[f'Tower {i+1} Type/Height'] = tower.tower_type_height if tower else None

            # Handle Power Information
            if exchange.power_info:
                row.update({
                    'WAPDA Ref Number': exchange.power_info.wapda_ref_number,
                    'Transformer Capacity': exchange.power_info.transformer_capacity,
                    'Transformer Earthing': exchange.power_info.transformer_earthing,
                    'Working Status (Power)': exchange.power_info.working_status,
                    'Name of NEs Connected': exchange.power_info.name_of_nes_connected,
                    'Load of Individual NE': exchange.power_info.load_of_individual_ne,
                })

            # Handle Rectifiers
            for i in range(max_rectifiers):
                rectifier = exchange.rectifiers[i] if i < len(exchange.rectifiers) else None
                row.update({
                    f'Rectifier {i+1} Make': rectifier.make_of_rectifier if rectifier else None,
                    f'Rectifier {i+1} Capacity': rectifier.rectifier_capacity if rectifier else None,
                    f'Rectifier {i+1} No of Modules': rectifier.no_of_modules if rectifier else None,
                    f'Rectifier {i+1} Capacity of Each Module': rectifier.capacity_of_each_module if rectifier else None,
                    f'Rectifier {i+1} Working Modules': rectifier.working_modules if rectifier else None,
                    f'Rectifier {i+1} Faulty Modules': rectifier.faulty_modules if rectifier else None,
                    f'Rectifier {i+1} Space for New Modules': rectifier.space_for_new_modules if rectifier else None,
                    f'Rectifier {i+1} Grounding of Rectifier': rectifier.grounding_of_rectifier if rectifier else None,
                    f'Rectifier {i+1} SPD in Rectifier': rectifier.spd_in_rectifier if rectifier else None,
                    f'Rectifier {i+1} SPD Model': rectifier.spd_model if rectifier else None,
                    f'Rectifier {i+1} Total Installed SPDs': rectifier.total_installed_spds if rectifier else None,
                    f'Rectifier {i+1} No of Faulty SPDs': rectifier.no_of_faulty_spds if rectifier else None
                })

            # Handle DGs
            for i in range(max_dgs):
                dg = exchange.dgs[i] if i < len(exchange.dgs) else None
                row.update({
                    f'DG {i+1} Installed DG': dg.installed_dg if dg else None,
                    f'DG {i+1} Engine Make': dg.engine_make if dg else None,
                    f'DG {i+1} Installation Year': dg.installation_year if dg else None,
                    f'DG {i+1} DG Status': dg.dg_status if dg else None,
                    f'DG {i+1} DG Starting Battery': dg.dg_starting_battery if dg else None,
                    f'DG {i+1} Smart Switch Installed': dg.smart_switch_installed if dg else None,
                    f'DG {i+1} ATS Installed': dg.ats_installed if dg else None,
                    f'DG {i+1} ATS Capacity': dg.ats_capacity if dg else None,
                    f'DG {i+1} Name of Faulty ATS Parts': dg.name_of_faulty_ats_parts if dg else None,
                    f'DG {i+1} No of Faulty ATS Parts': dg.no_of_faulty_ats_parts if dg else None,
                    f'DG {i+1} Load on DG P1': dg.load_on_dg_p1 if dg else None,
                    f'DG {i+1} Load on DG P2': dg.load_on_dg_p2 if dg else None,
                    f'DG {i+1} Load on DG P3': dg.load_on_dg_p3 if dg else None,
                    f'DG {i+1} Site Load Total': dg.site_load_total if dg else None,
                    f'DG {i+1} Site Load P1': dg.site_load_p1 if dg else None,
                    f'DG {i+1} Site Load P2': dg.site_load_p2 if dg else None,
                    f'DG {i+1} Site Load P3': dg.site_load_p3 if dg else None
                })

            # Handle Battery Banks
            for i in range(max_batteries):
                battery = exchange.battery_banks[i] if i < len(exchange.battery_banks) else None
                row.update({
                    f'Battery {i+1} Make of Battery': battery.make_of_battery if battery else None,
                    f'Battery {i+1} Battery Capacity': battery.battery_capacity if battery else None,
                    f'Battery {i+1} Battery Type': battery.battery_type if battery else None,
                    f'Battery {i+1} No of Cells/Bank': battery.no_of_cells_bank if battery else None,
                    f'Battery {i+1} Date of Installation': battery.date_of_installation if battery else None,
                    f'Battery {i+1} Load on Battery Bank': battery.load_on_battery_bank if battery else None,
                    f'Battery {i+1} Practical Backup Time': battery.practical_backup_time if battery else None,
                    f'Battery {i+1} Battery Installed (New/Used)': battery.battery_installed_new_or_used if battery else None,
                    f'Battery {i+1} Battery Moved From': battery.battery_moved_from if battery else None
                })

            # Handle AC Units
            for i in range(max_acs):
                ac = exchange.ac_units[i] if i < len(exchange.ac_units) else None
                row.update({
                    f'AC Unit {i+1} Location': ac.location_of_ac_unit if ac else None,
                    f'AC Unit {i+1} Working Status': ac.working_status if ac else None,
                    f'AC Unit {i+1} AC Make': ac.ac_make if ac else None,
                    f'AC Unit {i+1} Capacity (Tons)': ac.capacity_tons if ac else None,
                    f'AC Unit {i+1} Type of AC': ac.type_of_ac if ac else None,
                    f'AC Unit {i+1} Mount Type': ac.mount_type if ac else None,
                    f'AC Unit {i+1} Date of Installation': ac.date_of_installation if ac else None,
                    f'AC Unit {i+1} Sequence Controller Installed': ac.sequence_controller_installed if ac else None,
                    f'AC Unit {i+1} AC Load': ac.ac_load if ac else None,
                    f'AC Unit {i+1} Total AC Load': ac.total_ac_load if ac else None,
                    f'AC Unit {i+1} Fault Nature of AC Unit': ac.fault_nature_of_ac_unit if ac else None,
                    f'AC Unit {i+1} Estimate to Repair AC': ac.estimate_to_repair_ac if ac else None
                })

            # Handle Solar Information
            if exchange.solar_info:
                row.update({
                    'Total Solar Size': exchange.solar_info.total_solar_size,
                    'PV Solar Panel Capacity': exchange.solar_info.pv_solar_panel_capacity,
                    'No of PV Panels Installed': exchange.solar_info.no_of_pv_panels_installed,
                    'Make of PV Panels': exchange.solar_info.make_of_pv_panels,
                    'Charge Controller Make': exchange.solar_info.charge_controller_make
                })

            # Handle Colocation Information
            if exchange.colocation_info:
                row.update({
                    'Colocation': exchange.colocation_info.colocation,
                    'Name of Colocation Vendors': exchange.colocation_info.name_of_colocation_vendors,
                    'Load of Each Vendor': exchange.colocation_info.load_of_each_vendor,
                    'Total Load': exchange.colocation_info.total_load
                })

            # Handle Building Information
            if exchange.building_info:
                row.update({
                    'Building Status': exchange.building_info.building_status,
                    'Wall/Doors Condition': exchange.building_info.wall_doors_condition,
                })

            # Handle Alarms
            for i in range(max_alarms):
                alarm = exchange.alarms[i] if i < len(exchange.alarms) else None
                row.update({
                    f'Alarm {i+1} AC Main Failure': alarm.ac_main_failure if alarm else None,
                    f'Alarm {i+1} DC Low Voltages': alarm.dc_low_voltages if alarm else None,
                    f'Alarm {i+1} Rectifier Failure': alarm.rectifier_failure if alarm else None
                })

            # Handle Earthings
            for i in range(max_earthings):
                earthing = exchange.earthings[i] if i < len(exchange.earthings) else None
                row.update({
                    f'Earthing {i+1} Value': earthing.earthing_value if earthing else None,
                    f'Earthing {i+1} No of Pits': earthing.no_of_pits if earthing else None
                })

            # Handle Fire Extinguishers
            for i in range(max_fire_extinguishers):
                fire_ext = exchange.fire_extinguishers[i] if i < len(exchange.fire_extinguishers) else None
                row.update({
                    f'Fire Extinguisher {i+1} Installed': fire_ext.fe_installed if fire_ext else None,
                    f'Fire Extinguisher {i+1} No of FEs': fire_ext.no_of_fes if fire_ext else None,
                    f'Fire Extinguisher {i+1} Type of Gas': fire_ext.type_of_gas if fire_ext else None,
                    f'Fire Extinguisher {i+1} Date of Expiry': fire_ext.date_of_expiry if fire_ext else None
                })

            # Handle PMRs
            for i in range(max_pmrs):
                pmr = exchange.pmr_infos[i] if i < len(exchange.pmr_infos) else None
                row.update({
                    f'PMR {i+1} Performed': pmr.pmr_performed if pmr else None,
                    f'PMR {i+1} Last Performed Date': pmr.last_performed_date if pmr else None
                })

            data.append(row)

        df = pd.DataFrame(data)
        
        # Ensure columns are sorted for consistency
        df = df.reindex(sorted(df.columns), axis=1)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Exchanges')
            worksheet = writer.sheets['Exchanges']
            for idx, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(idx, idx, max_len)
        output.seek(0)
        
        return send_file(
            output,
            download_name='exchanges.xlsx',
            as_attachment=True,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except ImportError as e:
        flash(f'Export failed: Missing dependency - {str(e)}. Please ensure "xlsxwriter" is installed.')
        logging.error(f"Export failed due to missing dependency: {str(e)}")
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'Error exporting data: {str(e)}')
        logging.error(f"Error exporting data: {str(e)}")
        return redirect(url_for('index'))

@app.route('/view_exchanges')
@login_required
def view_exchanges():
    user_region = session.get('region')
    if user_region == "All":
        exchanges = GeneralInformation.query.all()
    else:
        exchanges = GeneralInformation.query.filter_by(domain=user_region).all()
    return render_template('view_exchanges.html', exchanges=exchanges)

if __name__ == '__main__':
    app.run(debug=True)