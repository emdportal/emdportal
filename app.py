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

# Initialize CSRF protection
#csrf = CSRFProtect(app)

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
            logging.info(f"User {session.get('username')} is adding a new exchange")
            last_sn = db.session.query(db.func.max(GeneralInformation.sn)).scalar() or 0
            sn = last_sn + 1

            user_region = session.get('region')
            domain = sanitize_text(request.form['domain']) if user_region == 'All' else user_region

            # Validate required fields
            if not request.form['site_name']:
                raise ValueError("Site name is required")
            if not request.form['wapda_ref_number']:
                raise ValueError("WAPDA reference number is required")

            # Validate site_category
            valid_site_categories = ['Tier-1', 'Tier-2', 'Tier-3', 'Tier-4', 'Tier-5', 'Platinum', 'Gold', 'Silver']
            site_category = request.form['site_category']
            if site_category not in valid_site_categories:
                raise ValueError(f"Invalid site category: {site_category}")

            general = GeneralInformation(
                sn=sn,
                region='RTR',
                domain=domain,
                site_name=sanitize_text(request.form['site_name']),
                site_lic=sanitize_text(request.form['site_lic']),
                flc=sanitize_text(request.form['flc']),
                site_type=request.form['site_type'],
                site_category=site_category,
                nes_installed=sanitize_text(request.form['nes_installed']),
                latitude=safe_float(request.form['latitude'], 'Latitude'),
                longitude=safe_float(request.form['longitude'], 'Longitude'),
                tower_available=request.form['tower_available'] if request.form['site_type'] in ['Exchange', 'Rpt/INDP'] else 'N/A',
            )
            
            if request.form['site_type'] == 'MSAG':
                general.nes_installed = 'MSAG'

            if general.tower_available == 'Yes':
                tower_types = request.form.getlist('tower_type_height[]')
                for tower_type in tower_types:
                    if tower_type:
                        tower = Tower(tower_type_height=sanitize_text(tower_type))
                        general.towers.append(tower)

            # Validate Power Information fields
            valid_working_status = ['Working', 'Faulty', 'Spare']
            working_status = request.form['working_status_power']
            if working_status not in valid_working_status:
                raise ValueError(f"Invalid working status: {working_status}")

            valid_yes_no = ['Yes', 'No']
            transformer_earthing = request.form['transformer_earthing']
            if transformer_earthing not in valid_yes_no:
                raise ValueError(f"Invalid transformer earthing: {transformer_earthing}")

            grounding_of_rectifier = request.form.getlist('grounding_of_rectifier[]')[0]
            if grounding_of_rectifier not in valid_yes_no:
                raise ValueError(f"Invalid grounding of rectifier: {grounding_of_rectifier}")

            spd_in_rectifier = request.form.getlist('spd_in_rectifier[]')[0]
            if spd_in_rectifier not in valid_yes_no:
                raise ValueError(f"Invalid SPD in rectifier: {spd_in_rectifier}")

            power_info = PowerInformation(
                wapda_ref_number=sanitize_text(request.form['wapda_ref_number']),
                transformer_capacity=sanitize_text(request.form['transformer_capacity']),
                transformer_earthing=transformer_earthing,
                working_status=working_status,
                load_of_individual_ne=safe_float(request.form['load_of_individual_ne'], 'Load of Individual NE'),
                name_of_nes_connected=sanitize_text(request.form['name_of_nes_connected']),
                make_of_rectifier=sanitize_text(request.form.getlist('make_of_rectifier[]')[0]) if request.form.getlist('make_of_rectifier[]') and request.form.getlist('make_of_rectifier[]')[0].strip() else None,
                rectifier_capacity=safe_float(request.form.getlist('rectifier_capacity[]')[0], 'Rectifier Capacity') if request.form.getlist('rectifier_capacity[]') and request.form.getlist('rectifier_capacity[]')[0].strip() else None,
                no_of_modules=safe_int(request.form.getlist('no_of_modules[]')[0], 'No of Modules') if request.form.getlist('no_of_modules[]') and request.form.getlist('no_of_modules[]')[0].strip() else None,
                capacity_of_each_module=safe_float(request.form.getlist('capacity_of_each_module[]')[0], 'Capacity of Each Module') if request.form.getlist('capacity_of_each_module[]') and request.form.getlist('capacity_of_each_module[]')[0].strip() else None,
                working_modules=safe_int(request.form.getlist('working_modules[]')[0], 'Working Modules') if request.form.getlist('working_modules[]') and request.form.getlist('working_modules[]')[0].strip() else None,
                faulty_modules=safe_int(request.form.getlist('faulty_modules[]')[0], 'Faulty Modules') if request.form.getlist('faulty_modules[]') and request.form.getlist('faulty_modules[]')[0].strip() else None,
                space_for_new_modules=safe_int(request.form.getlist('space_for_new_modules[]')[0], 'Space for New Modules') if request.form.getlist('space_for_new_modules[]') and request.form.getlist('space_for_new_modules[]')[0].strip() else None,
                grounding_of_rectifier=grounding_of_rectifier,
                spd_in_rectifier=spd_in_rectifier,
                spd_model=sanitize_text(request.form.getlist('spd_model[]')[0]) if request.form.getlist('spd_model[]') and request.form.getlist('spd_model[]')[0].strip() else None,
                total_installed_spds=safe_int(request.form.getlist('total_installed_spds[]')[0], 'Total Installed SPDs') if request.form.getlist('total_installed_spds[]') and request.form.getlist('total_installed_spds[]')[0].strip() else None,
                no_of_faulty_spds=safe_int(request.form.getlist('no_of_faulty_spds[]')[0], 'No of Faulty SPDs') if request.form.getlist('no_of_faulty_spds[]') and request.form.getlist('no_of_faulty_spds[]')[0].strip() else None
            )
            general.power_info = power_info

            # Validate DG Information fields
            valid_dg_status = ['Working', 'Faulty', 'Spare']
            installed_dgs = request.form.getlist('installed_dg[]')
            for i in range(len(installed_dgs)):
                if installed_dgs[i]:
                    dg_status = request.form.getlist('dg_status[]')[i]
                    if dg_status not in valid_dg_status:
                        raise ValueError(f"Invalid DG status: {dg_status}")

                    smart_switch_installed = request.form.getlist('smart_switch_installed[]')[i]
                    if smart_switch_installed not in valid_yes_no:
                        raise ValueError(f"Invalid smart switch installed: {smart_switch_installed}")

                    ats_installed = request.form.getlist('ats_installed[]')[i]
                    if ats_installed not in valid_yes_no:
                        raise ValueError(f"Invalid ATS installed: {ats_installed}")

                    dg = DGInformation(
                        installed_dg=sanitize_text(installed_dgs[i]),
                        engine_make=sanitize_text(request.form.getlist('engine_make[]')[i]),
                        installation_year=safe_int(request.form.getlist('installation_year[]')[i], 'Installation Year') if request.form.getlist('installation_year[]')[i].strip() else None,
                        dg_status=dg_status,
                        dg_starting_battery=sanitize_text(request.form.getlist('dg_starting_battery[]')[i]),
                        smart_switch_installed=smart_switch_installed,
                        ats_installed=ats_installed,
                        ats_capacity=sanitize_text(request.form.getlist('ats_capacity[]')[i]) or None,
                        name_of_faulty_ats_parts=sanitize_text(request.form.getlist('name_of_faulty_ats_parts[]')[i]) or None,
                        no_of_faulty_ats_parts=safe_int(request.form.getlist('no_of_faulty_ats_parts[]')[i], 'No of Faulty ATS Parts') if request.form.getlist('no_of_faulty_ats_parts[]')[i].strip() else None,
                        load_on_dg_p1=safe_float(request.form.getlist('load_on_dg_p1[]')[i], 'Load on DG P1') if request.form.getlist('load_on_dg_p1[]')[i].strip() else None,
                        load_on_dg_p2=safe_float(request.form.getlist('load_on_dg_p2[]')[i], 'Load on DG P2') if request.form.getlist('load_on_dg_p2[]')[i].strip() else None,
                        load_on_dg_p3=safe_float(request.form.getlist('load_on_dg_p3[]')[i], 'Load on DG P3') if request.form.getlist('load_on_dg_p3[]')[i].strip() else None,
                        site_load_total=safe_float(request.form.getlist('site_load_total[]')[i], 'Site Load Total') if request.form.getlist('site_load_total[]')[i].strip() else None,
                        site_load_p1=safe_float(request.form.getlist('site_load_p1[]')[i], 'Site Load P1') if request.form.getlist('site_load_p1[]')[i].strip() else None,
                        site_load_p2=safe_float(request.form.getlist('site_load_p2[]')[i], 'Site Load P2') if request.form.getlist('site_load_p2[]')[i].strip() else None,
                        site_load_p3=safe_float(request.form.getlist('site_load_p3[]')[i], 'Site Load P3') if request.form.getlist('site_load_p3[]')[i].strip() else None
                    )
                    general.dgs.append(dg)

            # Validate Battery Bank fields
            valid_battery_types = ['2V', '12V', '48V']
            valid_battery_install_types = ['New', 'Regenerated', 'Locally Arranged']
            makes_of_battery = request.form.getlist('make_of_battery[]')
            for i in range(len(makes_of_battery)):
                if makes_of_battery[i]:
                    battery_type = request.form.getlist('battery_type[]')[i]
                    if battery_type not in valid_battery_types:
                        raise ValueError(f"Invalid battery type: {battery_type}")

                    battery_installed_new_or_used = request.form.getlist('battery_installed_new_or_used[]')[i]
                    if battery_installed_new_or_used not in valid_battery_install_types:
                        raise ValueError(f"Invalid battery install type: {battery_installed_new_or_used}")

                    battery = BatteryBank(
                        make_of_battery=sanitize_text(makes_of_battery[i]),
                        battery_capacity=safe_float(request.form.getlist('battery_capacity[]')[i], 'Battery Capacity') if request.form.getlist('battery_capacity[]')[i].strip() else None,
                        battery_type=battery_type,
                        no_of_cells_bank=safe_int(request.form.getlist('no_of_cells_bank[]')[i], 'No of Cells/Bank') if request.form.getlist('no_of_cells_bank[]')[i].strip() else None,
                        date_of_installation=sanitize_text(request.form.getlist('date_of_installation_battery[]')[i]) or None,
                        load_on_battery_bank=safe_float(request.form.getlist('load_on_battery_bank[]')[i], 'Load on Battery Bank') if request.form.getlist('load_on_battery_bank[]')[i].strip() else None,
                        practical_backup_time=safe_float(request.form.getlist('practical_backup_time[]')[i], 'Practical Backup Time') if request.form.getlist('practical_backup_time[]')[i].strip() else None,
                        battery_installed_new_or_used=battery_installed_new_or_used,
                        battery_moved_from=sanitize_text(request.form.getlist('battery_moved_from[]')[i]) or None
                    )
                    general.battery_banks.append(battery)

            # Validate AC Unit fields
            valid_ac_status = ['Working', 'Faulty', 'Spare']
            locations = request.form.getlist('location_of_ac_unit[]')
            for i in range(len(locations)):
                if locations[i]:
                    working_status_ac = request.form.getlist('working_status_ac[]')[i]
                    if working_status_ac not in valid_ac_status:
                        raise ValueError(f"Invalid AC working status: {working_status_ac}")

                    sequence_controller_installed = request.form.getlist('sequence_controller_installed[]')[i]
                    if sequence_controller_installed not in valid_yes_no:
                        raise ValueError(f"Invalid sequence controller installed: {sequence_controller_installed}")

                    ac = ACUnit(
                        location_of_ac_unit=sanitize_text(locations[i]),
                        working_status=working_status_ac,
                        ac_make=sanitize_text(request.form.getlist('ac_make[]')[i]) or None,
                        capacity_tons=safe_float(request.form.getlist('capacity_tons[]')[i], 'Capacity (Tons)') if request.form.getlist('capacity_tons[]')[i].strip() else None,
                        type_of_ac=sanitize_text(request.form.getlist('type_of_ac[]')[i]) or None,
                        mount_type=sanitize_text(request.form.getlist('mount_type[]')[i]) or None,
                        date_of_installation=sanitize_text(request.form.getlist('date_of_installation_ac[]')[i]) or None,
                        sequence_controller_installed=sequence_controller_installed,
                        ac_load=safe_float(request.form.getlist('ac_load[]')[i], 'AC Load') if request.form.getlist('ac_load[]')[i].strip() else None,
                        total_ac_load=safe_float(request.form.getlist('total_ac_load[]')[i], 'Total AC Load') if request.form.getlist('total_ac_load[]')[i].strip() else None,
                        fault_nature_of_ac_unit=sanitize_text(request.form.getlist('fault_nature_of_ac_unit[]')[i]) or None,
                        estimate_to_repair_ac=safe_float(request.form.getlist('estimate_to_repair_ac[]')[i], 'Estimate to Repair AC') if request.form.getlist('estimate_to_repair_ac[]')[i].strip() else None
                    )
                    general.ac_units.append(ac)

            solar_info = SolarInformation(
                total_solar_size=safe_float(request.form['total_solar_size'], 'Total Solar Size'),
                pv_solar_panel_capacity=safe_float(request.form['pv_solar_panel_capacity'], 'PV Solar Panel Capacity'),
                no_of_pv_panels_installed=safe_int(request.form['no_of_pv_panels_installed'], 'No of PV Panels Installed'),
                make_of_pv_panels=sanitize_text(request.form['make_of_pv_panels']) or None,
                charge_controller_make=sanitize_text(request.form['charge_controller_make']) or None
            )
            general.solar_info = solar_info

            # Validate Colocation
            colocation = request.form['colocation']
            if colocation not in valid_yes_no:
                raise ValueError(f"Invalid colocation value: {colocation}")

            colocation_info = ColocationInformation(
                colocation=colocation,
                name_of_colocation_vendors=sanitize_text(request.form['name_of_colocation_vendors']) or None,
                load_of_each_vendor=safe_float(request.form['load_of_each_vendor'], 'Load of Each Vendor'),
                total_load=safe_float(request.form['total_load'], 'Total Load')
            )
            general.colocation_info = colocation_info

            building_info = BuildingInformation(
                building_status=sanitize_text(request.form['building_status']),
                wall_doors_condition=sanitize_text(request.form['wall_doors_condition'])
            )
            general.building_info = building_info

            # Validate Alarm Extension
            alarms = []
            ac_main_failures = request.form.getlist('ac_main_failure[]')
            for i in range(len(ac_main_failures)):
                ac_main_failure = ac_main_failures[i]
                dc_low_voltages = request.form.getlist('dc_low_voltages[]')[i]
                rectifier_failure = request.form.getlist('rectifier_failure[]')[i]

                if ac_main_failure not in valid_yes_no:
                    raise ValueError(f"Invalid AC main failure: {ac_main_failure}")
                if dc_low_voltages not in valid_yes_no:
                    raise ValueError(f"Invalid DC low voltages: {dc_low_voltages}")
                if rectifier_failure not in valid_yes_no:
                    raise ValueError(f"Invalid rectifier failure: {rectifier_failure}")

                alarm = AlarmExtension(
                    ac_main_failure=ac_main_failure,
                    dc_low_voltages=dc_low_voltages,
                    rectifier_failure=rectifier_failure
                )
                alarms.append(alarm)
            general.alarms = alarms

            # Earthing
            earthings = []
            earthing_values = request.form.getlist('earthing_value[]')
            for i in range(len(earthing_values)):
                if earthing_values[i]:
                    earthing = Earthing(
                        earthing_value=safe_float(earthing_values[i], 'Earthing Value'),
                        no_of_pits=safe_int(request.form.getlist('no_of_pits[]')[i], 'No of Pits')
                    )
                    earthings.append(earthing)
            general.earthings = earthings

            # Validate Fire Extinguisher
            fire_extinguishers = []
            fe_installeds = request.form.getlist('fe_installed[]')
            for i in range(len(fe_installeds)):
                fe_installed = fe_installeds[i]
                if fe_installed not in valid_yes_no:
                    raise ValueError(f"Invalid fire extinguisher installed: {fe_installed}")

                fire_ext = FireExtinguisher(
                    fe_installed=fe_installed,
                    no_of_fes=safe_int(request.form.getlist('no_of_fes[]')[i], 'No of FEs'),
                    type_of_gas=sanitize_text(request.form.getlist('type_of_gas[]')[i]) or None,
                    date_of_expiry=sanitize_text(request.form.getlist('date_of_expiry[]')[i]) or None
                )
                fire_extinguishers.append(fire_ext)
            general.fire_extinguishers = fire_extinguishers

            # Validate PMR Information
            pmr_infos = []
            pmr_performeds = request.form.getlist('pmr_performed[]')
            for i in range(len(pmr_performeds)):
                pmr_performed = pmr_performeds[i]
                if pmr_performed not in valid_yes_no:
                    raise ValueError(f"Invalid PMR performed: {pmr_performed}")

                pmr = PMRInformation(
                    pmr_performed=pmr_performed,
                    last_performed_date=sanitize_text(request.form.getlist('last_performed_date[]')[i]) or None
                )
                pmr_infos.append(pmr)
            general.pmr_infos = pmr_infos

            db.session.add(general)
            db.session.commit()
            flash('Exchange added successfully!')
            logging.info(f"Exchange SN {sn} added successfully by {session.get('username')}")
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error adding exchange by {session.get('username')}: {str(e)}")
            flash(f'Error adding exchange: {str(e)}')
            return redirect(url_for('add'))
    return render_template('add.html', general=None)

@app.route('/edit/<int:sn>', methods=['GET', 'POST'])
@login_required
def edit(sn):
    general = GeneralInformation.query.get_or_404(sn)
    user_region = session.get('region')
    
    if user_region != "All" and general.domain != user_region:
        flash('You do not have access to edit this exchange.')
        return redirect(url_for('index'))

    if request.method == 'POST':
        try:
            logging.info(f"User {session.get('username')} is editing exchange SN {sn}")
            with db.session.no_autoflush:
                general.region = 'RTR'
                general.domain = sanitize_text(request.form['domain']) if user_region == 'All' else user_region
                general.site_name = sanitize_text(request.form['site_name'])
                general.site_lic = sanitize_text(request.form['site_lic'])
                general.flc = sanitize_text(request.form['flc'])
                site_type = request.form['site_type']
                general.site_type = site_type
                
                # Validate required fields
                if not request.form['site_name']:
                    raise ValueError("Site name is required")
                if not request.form['wapda_ref_number']:
                    raise ValueError("WAPDA reference number is required")

                # Validate site_category
                valid_site_categories = ['Tier-1', 'Tier-2', 'Tier-3', 'Tier-4', 'Tier-5', 'Platinum', 'Gold', 'Silver']
                site_category = request.form['site_category']
                if site_category not in valid_site_categories:
                    raise ValueError(f"Invalid site category: {site_category}")
                general.site_category = site_category

                general.nes_installed = sanitize_text(request.form['nes_installed'])
                general.latitude = safe_float(request.form['latitude'], 'Latitude')
                general.longitude = safe_float(request.form['longitude'], 'Longitude')
                tower_available = request.form['tower_available'] if request.form['site_type'] in ['Exchange', 'Rpt/INDP'] else 'N/A'
                general.tower_available = tower_available
                if request.form['site_type'] == 'MSAG':
                    general.nes_installed = 'MSAG'

                if general.tower_available == 'Yes':
                    general.towers = []
                    tower_types = request.form.getlist('tower_type_height[]')
                    for tower_type in tower_types:
                        if tower_type:
                            tower = Tower(tower_type_height=sanitize_text(tower_type))
                            general.towers.append(tower)
                else:
                    general.towers = []

                if not general.power_info:
                    general.power_info = PowerInformation()

                # Validate Power Information fields
                valid_working_status = ['Working', 'Faulty', 'Spare']
                working_status = request.form['working_status_power']
                if working_status not in valid_working_status:
                    raise ValueError(f"Invalid working status: {working_status}")

                valid_yes_no = ['Yes', 'No']
                transformer_earthing = request.form['transformer_earthing']
                if transformer_earthing not in valid_yes_no:
                    raise ValueError(f"Invalid transformer earthing: {transformer_earthing}")

                grounding_of_rectifier = request.form.getlist('grounding_of_rectifier[]')[0]
                if grounding_of_rectifier not in valid_yes_no:
                    raise ValueError(f"Invalid grounding of rectifier: {grounding_of_rectifier}")

                spd_in_rectifier = request.form.getlist('spd_in_rectifier[]')[0]
                if spd_in_rectifier not in valid_yes_no:
                    raise ValueError(f"Invalid SPD in rectifier: {spd_in_rectifier}")

                general.power_info.wapda_ref_number = sanitize_text(request.form['wapda_ref_number'])
                general.power_info.transformer_capacity = sanitize_text(request.form['transformer_capacity'])
                general.power_info.transformer_earthing = transformer_earthing
                general.power_info.working_status = working_status
                general.power_info.load_of_individual_ne = safe_float(request.form['load_of_individual_ne'], 'Load of Individual NE')
                general.power_info.name_of_nes_connected = sanitize_text(request.form['name_of_nes_connected'])
                make_of_rectifiers = request.form.getlist('make_of_rectifier[]')
                general.power_info.make_of_rectifier = sanitize_text(make_of_rectifiers[0]) if make_of_rectifiers and make_of_rectifiers[0].strip() else None

                rectifier_capacities = request.form.getlist('rectifier_capacity[]')
                general.power_info.rectifier_capacity = safe_float(rectifier_capacities[0], 'Rectifier Capacity') if rectifier_capacities and rectifier_capacities[0].strip() else None

                no_of_modules_list = request.form.getlist('no_of_modules[]')
                general.power_info.no_of_modules = safe_int(no_of_modules_list[0], 'No of Modules') if no_of_modules_list and no_of_modules_list[0].strip() else None

                capacity_of_each_module_list = request.form.getlist('capacity_of_each_module[]')
                general.power_info.capacity_of_each_module = safe_float(capacity_of_each_module_list[0], 'Capacity of Each Module') if capacity_of_each_module_list and capacity_of_each_module_list[0].strip() else None

                working_modules_list = request.form.getlist('working_modules[]')
                general.power_info.working_modules = safe_int(working_modules_list[0], 'Working Modules') if working_modules_list and working_modules_list[0].strip() else None

                faulty_modules_list = request.form.getlist('faulty_modules[]')
                general.power_info.faulty_modules = safe_int(faulty_modules_list[0], 'Faulty Modules') if faulty_modules_list and faulty_modules_list[0].strip() else None

                space_for_new_modules_list = request.form.getlist('space_for_new_modules[]')
                general.power_info.space_for_new_modules = safe_int(space_for_new_modules_list[0], 'Space for New Modules') if space_for_new_modules_list and space_for_new_modules_list[0].strip() else None

                general.power_info.grounding_of_rectifier = grounding_of_rectifier
                general.power_info.spd_in_rectifier = spd_in_rectifier

                spd_models = request.form.getlist('spd_model[]')
                general.power_info.spd_model = sanitize_text(spd_models[0]) if spd_models and spd_models[0].strip() else None

                total_installed_spds_list = request.form.getlist('total_installed_spds[]')
                general.power_info.total_installed_spds = safe_int(total_installed_spds_list[0], 'Total Installed SPDs') if total_installed_spds_list and total_installed_spds_list[0].strip() else None

                no_of_faulty_spds_list = request.form.getlist('no_of_faulty_spds[]')
                general.power_info.no_of_faulty_spds = safe_int(no_of_faulty_spds_list[0], 'No of Faulty SPDs') if no_of_faulty_spds_list and no_of_faulty_spds_list[0].strip() else None

                # Validate DG Information fields
                valid_dg_status = ['Working', 'Faulty', 'Spare']
                general.dgs = []
                installed_dgs = request.form.getlist('installed_dg[]')
                for i in range(len(installed_dgs)):
                    if installed_dgs[i]:
                        dg_status = request.form.getlist('dg_status[]')[i]
                        if dg_status not in valid_dg_status:
                            raise ValueError(f"Invalid DG status: {dg_status}")

                        smart_switch_installed = request.form.getlist('smart_switch_installed[]')[i]
                        if smart_switch_installed not in valid_yes_no:
                            raise ValueError(f"Invalid smart switch installed: {smart_switch_installed}")

                        ats_installed = request.form.getlist('ats_installed[]')[i]
                        if ats_installed not in valid_yes_no:
                            raise ValueError(f"Invalid ATS installed: {ats_installed}")

                        dg = DGInformation(
                            installed_dg=sanitize_text(installed_dgs[i]),
                            engine_make=sanitize_text(request.form.getlist('engine_make[]')[i]),
                            installation_year=safe_int(request.form.getlist('installation_year[]')[i], 'Installation Year') if request.form.getlist('installation_year[]')[i].strip() else None,
                            dg_status=dg_status,
                            dg_starting_battery=sanitize_text(request.form.getlist('dg_starting_battery[]')[i]),
                            smart_switch_installed=smart_switch_installed,
                            ats_installed=ats_installed,
                            ats_capacity=sanitize_text(request.form.getlist('ats_capacity[]')[i]) or None,
                            name_of_faulty_ats_parts=sanitize_text(request.form.getlist('name_of_faulty_ats_parts[]')[i]) or None,
                            no_of_faulty_ats_parts=safe_int(request.form.getlist('no_of_faulty_ats_parts[]')[i], 'No of Faulty ATS Parts') if request.form.getlist('no_of_faulty_ats_parts[]')[i].strip() else None,
                            load_on_dg_p1=safe_float(request.form.getlist('load_on_dg_p1[]')[i], 'Load on DG P1') if request.form.getlist('load_on_dg_p1[]')[i].strip() else None,
                            load_on_dg_p2=safe_float(request.form.getlist('load_on_dg_p2[]')[i], 'Load on DG P2') if request.form.getlist('load_on_dg_p2[]')[i].strip() else None,
                            load_on_dg_p3=safe_float(request.form.getlist('load_on_dg_p3[]')[i], 'Load on DG P3') if request.form.getlist('load_on_dg_p3[]')[i].strip() else None,
                            site_load_total=safe_float(request.form.getlist('site_load_total[]')[i], 'Site Load Total') if request.form.getlist('site_load_total[]')[i].strip() else None,
                            site_load_p1=safe_float(request.form.getlist('site_load_p1[]')[i], 'Site Load P1') if request.form.getlist('site_load_p1[]')[i].strip() else None,
                            site_load_p2=safe_float(request.form.getlist('site_load_p2[]')[i], 'Site Load P2') if request.form.getlist('site_load_p2[]')[i].strip() else None,
                            site_load_p3=safe_float(request.form.getlist('site_load_p3[]')[i], 'Site Load P3') if request.form.getlist('site_load_p3[]')[i].strip() else None
                        )
                        general.dgs.append(dg)

                # Validate Battery Bank fields
                valid_battery_types = ['2V', '12V', '48V']
                valid_battery_install_types = ['New', 'Regenerated', 'Locally Arranged']
                general.battery_banks = []
                makes_of_battery = request.form.getlist('make_of_battery[]')
                for i in range(len(makes_of_battery)):
                    if makes_of_battery[i]:
                        battery_type = request.form.getlist('battery_type[]')[i]
                        if battery_type not in valid_battery_types:
                            raise ValueError(f"Invalid battery type: {battery_type}")

                        battery_installed_new_or_used = request.form.getlist('battery_installed_new_or_used[]')[i]
                        if battery_installed_new_or_used not in valid_battery_install_types:
                            raise ValueError(f"Invalid battery install type: {battery_installed_new_or_used}")

                        battery = BatteryBank(
                            make_of_battery=sanitize_text(makes_of_battery[i]),
                            battery_capacity=safe_float(request.form.getlist('battery_capacity[]')[i], 'Battery Capacity') if request.form.getlist('battery_capacity[]')[i].strip() else None,
                            battery_type=battery_type,
                            no_of_cells_bank=safe_int(request.form.getlist('no_of_cells_bank[]')[i], 'No of Cells/Bank') if request.form.getlist('no_of_cells_bank[]')[i].strip() else None,
                            date_of_installation=sanitize_text(request.form.getlist('date_of_installation_battery[]')[i]) or None,
                            load_on_battery_bank=safe_float(request.form.getlist('load_on_battery_bank[]')[i], 'Load on Battery Bank') if request.form.getlist('load_on_battery_bank[]')[i].strip() else None,
                            practical_backup_time=safe_float(request.form.getlist('practical_backup_time[]')[i], 'Practical Backup Time') if request.form.getlist('practical_backup_time[]')[i].strip() else None,
                            battery_installed_new_or_used=battery_installed_new_or_used,
                            battery_moved_from=sanitize_text(request.form.getlist('battery_moved_from[]')[i]) or None
                        )
                        general.battery_banks.append(battery)

                # Validate AC Unit fields
                valid_ac_status = ['Working', 'Faulty', 'Spare']
                general.ac_units = []
                locations = request.form.getlist('location_of_ac_unit[]')
                for i in range(len(locations)):
                    if locations[i]:
                        working_status_ac = request.form.getlist('working_status_ac[]')[i]
                        if working_status_ac not in valid_ac_status:
                            raise ValueError(f"Invalid AC working status: {working_status_ac}")

                        sequence_controller_installed = request.form.getlist('sequence_controller_installed[]')[i]
                        if sequence_controller_installed not in valid_yes_no:
                            raise ValueError(f"Invalid sequence controller installed: {sequence_controller_installed}")

                        ac = ACUnit(
                            location_of_ac_unit=sanitize_text(locations[i]),
                            working_status=working_status_ac,
                            ac_make=sanitize_text(request.form.getlist('ac_make[]')[i]) or None,
                            capacity_tons=safe_float(request.form.getlist('capacity_tons[]')[i], 'Capacity (Tons)') if request.form.getlist('capacity_tons[]')[i].strip() else None,
                            type_of_ac=sanitize_text(request.form.getlist('type_of_ac[]')[i]) or None,
                            mount_type=sanitize_text(request.form.getlist('mount_type[]')[i]) or None,
                            date_of_installation=sanitize_text(request.form.getlist('date_of_installation_ac[]')[i]) or None,
                            sequence_controller_installed=sequence_controller_installed,
                            ac_load=safe_float(request.form.getlist('ac_load[]')[i], 'AC Load') if request.form.getlist('ac_load[]')[i].strip() else None,
                            total_ac_load=safe_float(request.form.getlist('total_ac_load[]')[i], 'Total AC Load') if request.form.getlist('total_ac_load[]')[i].strip() else None,
                            fault_nature_of_ac_unit=sanitize_text(request.form.getlist('fault_nature_of_ac_unit[]')[i]) or None,
                            estimate_to_repair_ac=safe_float(request.form.getlist('estimate_to_repair_ac[]')[i], 'Estimate to Repair AC') if request.form.getlist('estimate_to_repair_ac[]')[i].strip() else None
                        )
                        general.ac_units.append(ac)

                if not general.solar_info:
                    general.solar_info = SolarInformation()
                general.solar_info.total_solar_size = safe_float(request.form['total_solar_size'], 'Total Solar Size')
                general.solar_info.pv_solar_panel_capacity = safe_float(request.form['pv_solar_panel_capacity'], 'PV Solar Panel Capacity')
                general.solar_info.no_of_pv_panels_installed = safe_int(request.form['no_of_pv_panels_installed'], 'No of PV Panels Installed')
                general.solar_info.make_of_pv_panels = sanitize_text(request.form['make_of_pv_panels']) or None
                general.solar_info.charge_controller_make = sanitize_text(request.form['charge_controller_make']) or None

                # Validate Colocation
                if not general.colocation_info:
                    general.colocation_info = ColocationInformation()
                colocation = request.form['colocation']
                if colocation not in valid_yes_no:
                    raise ValueError(f"Invalid colocation value: {colocation}")
                general.colocation_info.colocation = colocation
                general.colocation_info.name_of_colocation_vendors = sanitize_text(request.form['name_of_colocation_vendors']) or None
                general.colocation_info.load_of_each_vendor = safe_float(request.form['load_of_each_vendor'], 'Load of Each Vendor')
                general.colocation_info.total_load = safe_float(request.form['total_load'], 'Total Load')

                if not general.building_info:
                    general.building_info = BuildingInformation()
                general.building_info.building_status = sanitize_text(request.form['building_status'])
                general.building_info.wall_doors_condition = sanitize_text(request.form['wall_doors_condition'])

                # Validate Alarm Extension
                general.alarms = []
                ac_main_failures = request.form.getlist('ac_main_failure[]')
                for i in range(len(ac_main_failures)):
                    ac_main_failure = ac_main_failures[i]
                    dc_low_voltages = request.form.getlist('dc_low_voltages[]')[i]
                    rectifier_failure = request.form.getlist('rectifier_failure[]')[i]

                    if ac_main_failure not in valid_yes_no:
                        raise ValueError(f"Invalid AC main failure: {ac_main_failure}")
                    if dc_low_voltages not in valid_yes_no:
                        raise ValueError(f"Invalid DC low voltages: {dc_low_voltages}")
                    if rectifier_failure not in valid_yes_no:
                        raise ValueError(f"Invalid rectifier failure: {rectifier_failure}")

                    alarm = AlarmExtension(
                        ac_main_failure=ac_main_failure,
                        dc_low_voltages=dc_low_voltages,
                        rectifier_failure=rectifier_failure
                    )
                    general.alarms.append(alarm)

                # Update Earthing
                general.earthings = []
                earthing_values = request.form.getlist('earthing_value[]')
                for i in range(len(earthing_values)):
                    if earthing_values[i]:
                        earthing = Earthing(
                            earthing_value=safe_float(earthing_values[i], 'Earthing Value'),
                            no_of_pits=safe_int(request.form.getlist('no_of_pits[]')[i], 'No of Pits')
                        )
                        general.earthings.append(earthing)

                # Validate Fire Extinguisher
                general.fire_extinguishers = []
                fe_installeds = request.form.getlist('fe_installed[]')
                for i in range(len(fe_installeds)):
                    fe_installed = fe_installeds[i]
                    if fe_installed not in valid_yes_no:
                        raise ValueError(f"Invalid fire extinguisher installed: {fe_installed}")

                    fire_ext = FireExtinguisher(
                        fe_installed=fe_installed,
                        no_of_fes=safe_int(request.form.getlist('no_of_fes[]')[i], 'No of FEs'),
                        type_of_gas=sanitize_text(request.form.getlist('type_of_gas[]')[i]) or None,
                        date_of_expiry=sanitize_text(request.form.getlist('date_of_expiry[]')[i]) or None
                    )
                    general.fire_extinguishers.append(fire_ext)

                # Validate PMR Information
                general.pmr_infos = []
                pmr_performeds = request.form.getlist('pmr_performed[]')
                for i in range(len(pmr_performeds)):
                    pmr_performed = pmr_performeds[i]
                    if pmr_performed not in valid_yes_no:
                        raise ValueError(f"Invalid PMR performed: {pmr_performed}")

                    pmr = PMRInformation(
                        pmr_performed=pmr_performed,
                        last_performed_date=sanitize_text(request.form.getlist('last_performed_date[]')[i]) or None
                    )
                    general.pmr_infos.append(pmr)

            db.session.commit()
            flash('Exchange updated successfully!')
            logging.info(f"Exchange SN {sn} updated successfully by {session.get('username')}")
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error updating exchange SN {sn} by {session.get('username')}: {str(e)}")
            flash(f'Error updating exchange: {str(e)}')
            return redirect(url_for('edit', sn=sn))
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
                    'Rectifier Make': exchange.power_info.make_of_rectifier,
                    'Rectifier Capacity': exchange.power_info.rectifier_capacity,
                    'No of Modules': exchange.power_info.no_of_modules,
                    'Capacity of Each Module': exchange.power_info.capacity_of_each_module,
                    'Working Modules': exchange.power_info.working_modules,
                    'Faulty Modules': exchange.power_info.faulty_modules,
                    'Space for New Modules': exchange.power_info.space_for_new_modules,
                    'Grounding of Rectifier': exchange.power_info.grounding_of_rectifier,
                    'SPD in Rectifier': exchange.power_info.spd_in_rectifier,
                    'SPD Model': exchange.power_info.spd_model,
                    'Total Installed SPDs': exchange.power_info.total_installed_spds,
                    'No of Faulty SPDs': exchange.power_info.no_of_faulty_spds
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