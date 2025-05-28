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
from datetime import datetime

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

# Define logger for use throughout the app
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

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
    created_by = db.Column(db.String(50))
    updated_by = db.Column(db.String(50))
    updated_at = db.Column(db.DateTime)
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
    created_by = db.Column(db.String(50))
    updated_by = db.Column(db.String(50))
    updated_at = db.Column(db.DateTime)

class PowerInformation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn', ondelete='CASCADE'))
    wapda_ref_number = db.Column(db.String(50))
    transformer_capacity = db.Column(db.String(50))
    transformer_earthing = db.Column(db.String(10))  # Yes/No
    working_status = db.Column(db.String(20))  # Working/Faulty/Spare
    load_of_individual_ne = db.Column(db.Float, nullable=True)
    name_of_nes_connected = db.Column(db.Text)
    rectifiers = db.Column(db.JSON, nullable=True)  # JSONB in PostgreSQL
    created_by = db.Column(db.String(50))
    updated_by = db.Column(db.String(50))
    updated_at = db.Column(db.DateTime)

class DGInformation(db.Model):
    __tablename__ = 'dg'
    id = db.Column(db.Integer, primary_key=True)
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn', ondelete='CASCADE'))
    installed_dg = db.Column(db.String(50))
    engine_make = db.Column(db.String(50))
    installation_year = db.Column(db.Integer, nullable=True)
    dg_status = db.Column(db.String(20))  # Working/Faulty/Spare
    dg_starting_battery = db.Column(db.String(50))
    smart_switch_installed = db.Column(db.Boolean, nullable=True)  # Changed from String to Boolean
    ats_installed = db.Column(db.Boolean, nullable=True)  # Changed from String to Boolean
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
    created_by = db.Column(db.String(50))
    updated_by = db.Column(db.String(50))
    updated_at = db.Column(db.DateTime)

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
    created_by = db.Column(db.String(50))
    updated_by = db.Column(db.String(50))
    updated_at = db.Column(db.DateTime)

class BatteryBankHistory(db.Model):
    __tablename__ = 'battery_bank_history'
    history_id = db.Column(db.Integer, primary_key=True)
    original_id = db.Column(db.Integer, nullable=False)
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn', ondelete='CASCADE'))
    make_of_battery = db.Column(db.String(50))
    battery_capacity = db.Column(db.Float, nullable=True)
    battery_type = db.Column(db.String(10))
    no_of_cells_bank = db.Column(db.Integer, nullable=True)
    date_of_installation = db.Column(db.String(50))
    load_on_battery_bank = db.Column(db.Float, nullable=True)
    practical_backup_time = db.Column(db.Float, nullable=True)
    battery_installed_new_or_used = db.Column(db.String(20))
    battery_moved_from = db.Column(db.String(100))
    created_by = db.Column(db.String(50))
    updated_by = db.Column(db.String(50))
    updated_at = db.Column(db.DateTime)
    archived_at = db.Column(db.DateTime, default=datetime.utcnow)

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
    sequence_controller_installed = db.Column(db.String(10), nullable=True)  # Changed back to String for Yes/No
    ac_load = db.Column(db.Float, nullable=True)
    total_ac_load = db.Column(db.Float, nullable=True)
    fault_nature_of_ac_unit = db.Column(db.String(100))
    estimate_to_repair_ac = db.Column(db.Float, nullable=True)
    created_by = db.Column(db.String(50))
    updated_by = db.Column(db.String(50))
    updated_at = db.Column(db.DateTime)

class SolarInformation(db.Model):
    __tablename__ = 'installed_solar_information'
    id = db.Column(db.Integer, primary_key=True)
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn', ondelete='CASCADE'))
    total_solar_size = db.Column(db.Float, nullable=True)
    pv_solar_panel_capacity = db.Column(db.Float, nullable=True)
    no_of_pv_panels_installed = db.Column(db.Integer, nullable=True)
    make_of_pv_panels = db.Column(db.String(50))
    charge_controller_make = db.Column(db.String(50))
    created_by = db.Column(db.String(50))
    updated_by = db.Column(db.String(50))
    updated_at = db.Column(db.DateTime)

class ColocationInformation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn', ondelete='CASCADE'))
    colocation = db.Column(db.String(10), default='No')  # Yes/No
    name_of_colocation_vendors = db.Column(db.Text)
    load_of_each_vendor = db.Column(db.Float, nullable=True)
    total_load = db.Column(db.Float, nullable=True)
    created_by = db.Column(db.String(50))
    updated_by = db.Column(db.String(50))
    updated_at = db.Column(db.DateTime)

class BuildingInformation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn', ondelete='CASCADE'))
    building_status = db.Column(db.String(100))
    wall_doors_condition = db.Column(db.String(100))
    created_by = db.Column(db.String(50))
    updated_by = db.Column(db.String(50))
    updated_at = db.Column(db.DateTime)

class AlarmExtension(db.Model):
    __tablename__ = 'alarm_extension'
    id = db.Column(db.Integer, primary_key=True)
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn', ondelete='CASCADE'))
    ac_main_failure = db.Column(db.String(10), nullable=True)  # Yes/No
    dc_low_voltages = db.Column(db.String(10), nullable=True)  # Yes/No
    rectifier_failure = db.Column(db.String(10), nullable=True)  # Yes/No
    created_by = db.Column(db.String(50))
    updated_by = db.Column(db.String(50))
    updated_at = db.Column(db.DateTime)

class Earthing(db.Model):
    __tablename__ = 'earthing'
    id = db.Column(db.Integer, primary_key=True)
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn', ondelete='CASCADE'))
    earthing_value = db.Column(db.Float, nullable=True)
    no_of_pits = db.Column(db.Integer, nullable=True)
    created_by = db.Column(db.String(50))
    updated_by = db.Column(db.String(50))
    updated_at = db.Column(db.DateTime)

class FireExtinguisher(db.Model):
    __tablename__ = 'fire_extinguisher'
    id = db.Column(db.Integer, primary_key=True)
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn', ondelete='CASCADE'))
    fe_installed = db.Column(db.String(10), nullable=True)  # Yes/No
    no_of_fes = db.Column(db.Integer, nullable=True)
    type_of_gas = db.Column(db.String(50), nullable=True)
    date_of_expiry = db.Column(db.String(50), nullable=True)
    created_by = db.Column(db.String(50))
    updated_by = db.Column(db.String(50))
    updated_at = db.Column(db.DateTime)

class PMRInformation(db.Model):
    __tablename__ = 'pmr_information'
    id = db.Column(db.Integer, primary_key=True)
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn', ondelete='CASCADE'))
    pmr_performed = db.Column(db.String(10), nullable=True)  # Yes/No
    last_performed_date = db.Column(db.String(50), nullable=True)
    created_by = db.Column(db.String(50))
    updated_by = db.Column(db.String(50))
    updated_at = db.Column(db.DateTime)

class PMRInformationHistory(db.Model):
    __tablename__ = 'pmr_information_history'
    history_id = db.Column(db.Integer, primary_key=True)
    original_id = db.Column(db.Integer, nullable=False)
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn', ondelete='CASCADE'))
    pmr_performed = db.Column(db.String(10), nullable=True)
    last_performed_date = db.Column(db.String(50), nullable=True)
    created_by = db.Column(db.String(50))
    updated_by = db.Column(db.String(50))
    updated_at = db.Column(db.DateTime)
    archived_at = db.Column(db.DateTime, default=datetime.utcnow)

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

        # Fetch total installed DGs and their status breakdown
        installed_dgs_query = db.session.query(DGInformation).filter(DGInformation.installed_dg.isnot(None), DGInformation.installed_dg != '')
        if user_region != "All":
            installed_dgs_query = installed_dgs_query.join(GeneralInformation).filter(GeneralInformation.domain == user_region)
        installed_dgs = installed_dgs_query.all()
        total_installed_dgs = len(installed_dgs)
        
        # DG Status breakdown
        dg_status_counts = {'Working': 0, 'Faulty': 0, 'Spare': 0}
        for dg in installed_dgs:
            status = dg.dg_status
            if status in dg_status_counts:
                dg_status_counts[status] += 1

        # Fetch count of sites with solar data (instead of sum)
        solar_query = db.session.query(GeneralInformation.sn).join(SolarInformation).filter(SolarInformation.total_solar_size.isnot(None))
        if user_region != "All":
            solar_query = solar_query.filter(GeneralInformation.domain == user_region)
        total_solar_sites = solar_query.distinct().count()  # Count unique sites with solar data

        # Calculate total battery cells from Battery Bank Information
        battery_query = db.session.query(BatteryBank).join(GeneralInformation)
        if user_region != "All":
            battery_query = battery_query.filter(GeneralInformation.domain == user_region)
        total_battery_cells = battery_query.with_entities(db.func.coalesce(db.func.sum(BatteryBank.no_of_cells_bank), 0)).scalar()

        # Calculate total fire extinguishers from Fire Extinguisher
        fe_query = db.session.query(FireExtinguisher).join(GeneralInformation)
        if user_region != "All":
            fe_query = fe_query.filter(GeneralInformation.domain == user_region)
        total_fire_extinguishers = fe_query.with_entities(db.func.coalesce(db.func.sum(FireExtinguisher.no_of_fes), 0)).scalar()

        # Calculate AC status counts from AC Unit Information
        ac_query = db.session.query(ACUnit).join(GeneralInformation)
        if user_region != "All":
            ac_query = ac_query.filter(GeneralInformation.domain == user_region)
        ac_units = ac_query.all()
        ac_status_counts = {'Working': 0, 'Faulty': 0, 'Spare': 0}
        for ac in ac_units:
            status = ac.working_status
            if status in ac_status_counts:
                ac_status_counts[status] += 1

        # Additional data for new charts
        battery_capacity_by_region = {}
        solar_sites_by_region = {}
        fe_count_by_region = {}
        for region in region_labels:
            region_exchanges = GeneralInformation.query.filter_by(domain=region).all()
            battery_capacity_by_region[region] = db.session.query(db.func.coalesce(db.func.sum(BatteryBank.battery_capacity), 0)).join(GeneralInformation).filter(GeneralInformation.domain == region).scalar()
            solar_sites_by_region[region] = db.session.query(GeneralInformation.sn).join(SolarInformation).filter(SolarInformation.total_solar_size.isnot(None), GeneralInformation.domain == region).distinct().count()
            fe_count_by_region[region] = db.session.query(db.func.coalesce(db.func.sum(FireExtinguisher.no_of_fes), 0)).join(GeneralInformation).filter(GeneralInformation.domain == region).scalar()

        return render_template('index.html',
                             exchanges=exchanges,
                             region_labels=region_labels,
                             region_counts=region_counts,
                             year_labels=year_labels,
                             year_counts=year_counts,
                             total_exchanges=total_exchanges,
                             total_installed_dgs=total_installed_dgs,
                             dg_status_counts=dg_status_counts,
                             total_solar_sites=total_solar_sites,
                             total_battery_cells=total_battery_cells,
                             total_fire_extinguishers=total_fire_extinguishers,
                             ac_status_counts=ac_status_counts,
                             battery_capacity_by_region=battery_capacity_by_region,
                             solar_sites_by_region=solar_sites_by_region,
                             fe_count_by_region=fe_count_by_region)
    except Exception as e:
        logging.error(f"Error in index route: {str(e)}")
        flash(f"Error: {str(e)}")
        return redirect(url_for('index'))

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        try:
            # Define validation lists
            valid_yes_no = ['Yes', 'No']
            valid_working_status = ['Working', 'Faulty', 'Spare']
            valid_dg_status = ['Working', 'Faulty', 'Spare']
            valid_battery_types = ['2V', '12V', '48V']
            valid_battery_installation = ['New', 'Regenerated', 'Locally Arranged']

            # Get the logged-in user
            username = session.get('username', 'unknown_user')

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

            # Create GeneralInformation instance with tracking fields
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
                created_by=username,
                updated_by=username,
                updated_at=datetime.utcnow()
            )

            db.session.add(general)

            # Tower Information
            tower_types = request.form.getlist('tower_type_height[]')
            for tower_type in tower_types:
                if tower_type.strip():
                    tower = Tower(
                        general_id=general.sn,
                        tower_type_height=tower_type,
                        created_by=username,
                        updated_by=username,
                        updated_at=datetime.utcnow()
                    )
                    db.session.add(tower)

            # Power Information with Rectifiers
            make_of_rectifiers = request.form.getlist('make_of_rectifier[]')
            if make_of_rectifiers and any(m.strip() for m in make_of_rectifiers):
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

                # Validate lengths of rectifier-related lists
                expected_length = len(make_of_rectifiers)
                lists_to_check = [
                    (rectifier_capacities, 'rectifier_capacity[]'),
                    (no_of_modules, 'no_of_modules[]'),
                    (capacity_of_each_module, 'capacity_of_each_module[]'),
                    (working_modules, 'working_modules[]'),
                    (faulty_modules, 'faulty_modules[]'),
                    (space_for_new_modules, 'space_for_new_modules[]'),
                    (grounding_of_rectifiers, 'grounding_of_rectifier[]'),
                    (spd_in_rectifiers, 'spd_in_rectifier[]'),
                    (spd_models, 'spd_model[]'),
                    (total_installed_spds, 'total_installed_spds[]'),
                    (no_of_faulty_spds, 'no_of_faulty_spds[]')
                ]

                for lst, name in lists_to_check:
                    if len(lst) != expected_length:
                        raise ValueError(f"Mismatch in rectifier field lengths: {name} has {len(lst)} entries, expected {expected_length}")

                rectifiers_data = []
                for i in range(expected_length):
                    if not make_of_rectifiers[i].strip():
                        continue
                    grounding = grounding_of_rectifiers[i] if grounding_of_rectifiers[i] in valid_yes_no else None
                    spd = spd_in_rectifiers[i] if spd_in_rectifiers[i] in valid_yes_no else None
                    rectifier = {
                        'make_of_rectifier': make_of_rectifiers[i] or None,
                        'rectifier_capacity': safe_float(rectifier_capacities[i], 'rectifier_capacity') if rectifier_capacities[i].strip() else None,
                        'no_of_modules': safe_int(no_of_modules[i], 'no_of_modules') if no_of_modules[i].strip() else None,
                        'capacity_of_each_module': safe_float(capacity_of_each_module[i], 'capacity_of_each_module') if capacity_of_each_module[i].strip() else None,
                        'working_modules': safe_int(working_modules[i], 'working_modules') if working_modules[i].strip() else None,
                        'faulty_modules': safe_int(faulty_modules[i], 'faulty_modules') if faulty_modules[i].strip() else None,
                        'space_for_new_modules': safe_int(space_for_new_modules[i], 'space_for_new_modules') if space_for_new_modules[i].strip() else None,
                        'grounding_of_rectifier': grounding,
                        'spd_in_rectifier': spd,
                        'spd_model': spd_models[i] if spd_models[i].strip() else None,
                        'total_installed_spds': safe_int(total_installed_spds[i], 'total_installed_spds') if total_installed_spds[i].strip() else None,
                        'no_of_faulty_spds': safe_int(no_of_faulty_spds[i], 'no_of_faulty_spds') if no_of_faulty_spds[i].strip() else None
                    }
                    rectifiers_data.append(rectifier)
                power_info = PowerInformation(
                    general_id=general.sn,
                    wapda_ref_number=request.form.get('wapda_ref_number') or None,
                    transformer_capacity=request.form.get('transformer_capacity') or None,
                    transformer_earthing=request.form.get('transformer_earthing') or None,
                    working_status=request.form.get('working_status_power') or None,
                    name_of_nes_connected=request.form.get('name_of_nes_connected') or None,
                    load_of_individual_ne=safe_float(request.form.get('load_of_individual_ne'), 'load_of_individual_ne') if request.form.get('load_of_individual_ne') else None,
                    rectifiers=rectifiers_data if rectifiers_data else None,
                    created_by=username,
                    updated_by=username,
                    updated_at=datetime.utcnow()
                )
            else:
                power_info = PowerInformation(
                    general_id=general.sn,
                    wapda_ref_number=request.form.get('wapda_ref_number') or None,
                    transformer_capacity=request.form.get('transformer_capacity') or None,
                    transformer_earthing=request.form.get('transformer_earthing') or None,
                    working_status=request.form.get('working_status_power') or None,
                    name_of_nes_connected=request.form.get('name_of_nes_connected') or None,
                    load_of_individual_ne=safe_float(request.form.get('load_of_individual_ne'), 'load_of_individual_ne') if request.form.get('load_of_individual_ne') else None,
                    rectifiers=None,
                    created_by=username,
                    updated_by=username,
                    updated_at=datetime.utcnow()
                )
            db.session.add(power_info)

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

                for i in range(len(installed_dgs)):
                    if not installed_dgs[i].strip():
                        continue
                    dg_status = dg_statuses[i] if dg_statuses[i] in valid_dg_status else None
                    smart_switch = True if smart_switch_installeds[i].lower() == 'yes' else False if smart_switch_installeds[i].lower() == 'no' else None
                    ats = True if ats_installeds[i].lower() == 'yes' else False if ats_installeds[i].lower() == 'no' else None
                    dg = DGInformation(
                        general_id=general.sn,
                        installed_dg=installed_dgs[i] or None,
                        engine_make=engine_makes[i] if engine_makes[i].strip() else None,
                        installation_year=safe_int(installation_years[i], 'installation_year') if installation_years[i].strip() else None,
                        dg_status=dg_status,
                        dg_starting_battery=dg_starting_batteries[i] if dg_starting_batteries[i].strip() else None,
                        smart_switch_installed=smart_switch,
                        ats_installed=ats,
                        ats_capacity=ats_capacities[i] if ats_capacities[i].strip() else None,
                        name_of_faulty_ats_parts=name_of_faulty_ats_parts[i] if name_of_faulty_ats_parts[i].strip() else None,
                        no_of_faulty_ats_parts=safe_int(no_of_faulty_ats_parts[i], 'no_of_faulty_ats_parts') if no_of_faulty_ats_parts[i].strip() else None,
                        load_on_dg_p1=safe_float(load_on_dg_p1s[i], 'load_on_dg_p1') if load_on_dg_p1s[i].strip() else None,
                        load_on_dg_p2=safe_float(load_on_dg_p2s[i], 'load_on_dg_p2') if load_on_dg_p2s[i].strip() else None,
                        load_on_dg_p3=safe_float(load_on_dg_p3s[i], 'load_on_dg_p3') if load_on_dg_p3s[i].strip() else None,
                        site_load_total=safe_float(site_load_totals[i], 'site_load_total') if site_load_totals[i].strip() else None,
                        site_load_p1=safe_float(site_load_p1s[i], 'site_load_p1') if site_load_p1s[i].strip() else None,
                        site_load_p2=safe_float(site_load_p2s[i], 'site_load_p2') if site_load_p2s[i].strip() else None,
                        site_load_p3=safe_float(site_load_p3s[i], 'site_load_p3') if site_load_p3s[i].strip() else None,
                        created_by=username,
                        updated_by=username,
                        updated_at=datetime.utcnow()
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

                for i in range(len(make_of_batteries)):
                    if not make_of_batteries[i].strip():
                        continue
                    battery_type = battery_types[i] if battery_types[i] in valid_battery_types else None
                    battery_installation = battery_installed_new_or_useds[i] if battery_installed_new_or_useds[i] in valid_battery_installation else None
                    battery = BatteryBank(
                        general_id=general.sn,
                        make_of_battery=make_of_batteries[i] or None,
                        battery_capacity=safe_float(battery_capacities[i], 'battery_capacity') if battery_capacities[i].strip() else None,
                        battery_type=battery_type,
                        no_of_cells_bank=safe_int(no_of_cells_banks[i], 'no_of_cells_bank') if no_of_cells_banks[i].strip() else None,
                        date_of_installation=date_of_installations[i] if date_of_installations[i].strip() else None,
                        load_on_battery_bank=safe_float(load_on_battery_banks[i], 'load_on_battery_bank') if load_on_battery_banks[i].strip() else None,
                        practical_backup_time=safe_float(practical_backup_times[i], 'practical_backup_time') if practical_backup_times[i].strip() else None,
                        battery_installed_new_or_used=battery_installation,
                        battery_moved_from=battery_moved_froms[i] if battery_moved_froms[i].strip() else None,
                        created_by=username,
                        updated_by=username,
                        updated_at=datetime.utcnow()
                    )
                    db.session.add(battery)

            # AC Unit Information
            with db.session.no_autoflush:
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
                            capacity_tons=safe_float(capacity_tons[i], 'capacity_tons') if capacity_tons[i].strip() else None,
                            type_of_ac=type_of_acs[i] if type_of_acs[i].strip() else None,
                            mount_type=mount_types[i] if mount_types[i].strip() else None,
                            date_of_installation=date_of_installation_acs[i] if date_of_installation_acs[i].strip() else None,
                            sequence_controller_installed=sequence_controller,
                            ac_load=safe_float(ac_loads[i], 'ac_load') if ac_loads[i].strip() else None,
                            total_ac_load=safe_float(total_ac_loads[i], 'total_ac_load') if total_ac_loads[i].strip() else None,
                            fault_nature_of_ac_unit=fault_nature_of_ac_units[i] if fault_nature_of_ac_units[i].strip() else None,
                            estimate_to_repair_ac=safe_float(estimate_to_repair_acs[i], 'estimate_to_repair_ac') if estimate_to_repair_acs[i].strip() else None,
                            created_by=username,
                            updated_by=username,
                            updated_at=datetime.utcnow()
                        )
                        db.session.add(ac_unit)

            # Solar Information
            solar_info = SolarInformation(
                general_id=general.sn,
                total_solar_size=safe_float(request.form.get('total_solar_size'), 'total_solar_size') if request.form.get('total_solar_size') else None,
                pv_solar_panel_capacity=safe_float(request.form.get('pv_solar_panel_capacity'), 'pv_solar_panel_capacity') if request.form.get('pv_solar_panel_capacity') else None,
                no_of_pv_panels_installed=safe_int(request.form.get('no_of_pv_panels_installed'), 'no_of_pv_panels_installed') if request.form.get('no_of_pv_panels_installed') else None,
                make_of_pv_panels=request.form.get('make_of_pv_panels') or None,
                charge_controller_make=request.form.get('charge_controller_make') or None,
                created_by=username,
                updated_by=username,
                updated_at=datetime.utcnow()
            )
            db.session.add(solar_info)

            # Colocation Information
            colocation = request.form.get('colocation')
            colocation_info = ColocationInformation(
                general_id=general.sn,
                colocation=colocation,
                name_of_colocation_vendors=request.form.get('name_of_colocation_vendors') or None,
                load_of_each_vendor=safe_float(request.form.get('load_of_each_vendor'), 'load_of_each_vendor') if request.form.get('load_of_each_vendor') else None,
                total_load=safe_float(request.form.get('total_load'), 'total_load') if request.form.get('total_load') else None,
                created_by=username,
                updated_by=username,
                updated_at=datetime.utcnow()
            )
            db.session.add(colocation_info)

            # Building Information
            building_info = BuildingInformation(
                general_id=general.sn,
                building_status=request.form.get('building_status') or None,
                wall_doors_condition=request.form.get('wall_doors_condition') or None,
                created_by=username,
                updated_by=username,
                updated_at=datetime.utcnow()
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
                        rectifier_failure=rectifier_failure,
                        created_by=username,
                        updated_by=username,
                        updated_at=datetime.utcnow()
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
                        earthing_value=safe_float(earthing_values[i], 'earthing_value') if earthing_values[i].strip() else None,
                        no_of_pits=safe_int(no_of_pits[i], 'no_of_pits') if no_of_pits[i].strip() else None,
                        created_by=username,
                        updated_by=username,
                        updated_at=datetime.utcnow()
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
                        no_of_fes=safe_int(no_of_fes[i], 'no_of_fes') if no_of_fes[i].strip() else None,
                        type_of_gas=type_of_gases[i] if type_of_gases[i].strip() else None,
                        date_of_expiry=date_of_expiries[i] if date_of_expiries[i].strip() else None,
                        created_by=username,
                        updated_by=username,
                        updated_at=datetime.utcnow()
                    )
                    db.session.add(fire_ext)

            # PMR Information
            pmr_performed = request.form.get('pmr_performed')
            last_performed_date = request.form.get('last_performed_date') or None
            if pmr_performed and pmr_performed.strip():
                pmr_performed = pmr_performed if pmr_performed in valid_yes_no else None
                last_performed_date = last_performed_date if pmr_performed == 'Yes' and last_performed_date.strip() else None
                pmr = PMRInformation(
                    general_id=general.sn,
                    pmr_performed=pmr_performed,
                    last_performed_date=last_performed_date,
                    created_by=username,
                    updated_by=username,
                    updated_at=datetime.utcnow()
                )
                db.session.add(pmr)

            db.session.commit()
            flash('Exchange added successfully!', 'success')
            logging.info(f"User {username} added exchange SN {general.sn}")
            return redirect(url_for('index'))

        except ValueError as e:
            db.session.rollback()
            flash(str(e), 'error')
            logging.error(f"Validation error adding exchange by {username}: {str(e)}")
        except Exception as e:
            db.session.rollback()
            error_msg = f"Error adding exchange: {str(e)}\nTraceback: {traceback.format_exc()}"
            flash(error_msg, 'error')
            logging.error(error_msg)

    return render_template('add.html', general=None)
    
@app.route('/edit/<int:sn>', methods=['GET', 'POST'])
@login_required
def edit(sn):
    general = GeneralInformation.query.get_or_404(sn)
    if request.method == 'POST':
        try:
            # Define validation lists
            valid_yes_no = ['Yes', 'No']
            valid_working_status = ['Working', 'Faulty', 'Spare']
            valid_dg_status = ['Working', 'Faulty', 'Spare']
            valid_battery_types = ['2V', '12V', '48V']
            valid_battery_installation = ['New', 'Regenerated', 'Locally Arranged']

            # Get the logged-in user
            username = session.get('username', 'unknown_user')

            # General Information
            general.region = request.form.get('region')
            general.domain = request.form.get('domain')
            general.site_name = request.form.get('site_name')
            general.site_lic = request.form.get('site_lic') or None
            general.flc = request.form.get('flc') or None
            general.site_type = request.form.get('site_type')
            general.site_category = request.form.get('site_category')
            general.nes_installed = request.form.get('nes_installed') or None
            general.latitude = float(request.form.get('latitude')) if request.form.get('latitude') else None
            general.longitude = float(request.form.get('longitude')) if request.form.get('longitude') else None
            general.tower_available = request.form.get('tower_available')
            general.updated_by = username
            general.updated_at = datetime.utcnow()

            # Validate required fields
            if not all([general.domain, general.site_name, general.site_type, general.site_category]):
                raise ValueError("Missing required general information fields")

            # Tower Information
            Tower.query.filter_by(general_id=general.sn).delete()
            tower_types = request.form.getlist('tower_type_height[]')
            for tower_type in tower_types:
                if tower_type.strip():
                    tower = Tower(
                        tower_type_height=tower_type,
                        general_id=general.sn,
                        created_by=username,
                        updated_by=username,
                        updated_at=datetime.utcnow()
                    )
                    db.session.add(tower)

            # Power Information with Rectifiers
            if not general.power_info:
                general.power_info = PowerInformation(general_id=general.sn)

            make_of_rectifiers = request.form.getlist('make_of_rectifier[]')
            if make_of_rectifiers and any(m.strip() for m in make_of_rectifiers):
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

                expected_length = len(make_of_rectifiers)
                lists_to_check = [
                    (rectifier_capacities, 'rectifier_capacity[]'),
                    (no_of_modules, 'no_of_modules[]'),
                    (capacity_of_each_module, 'capacity_of_each_module[]'),
                    (working_modules, 'working_modules[]'),
                    (faulty_modules, 'faulty_modules[]'),
                    (space_for_new_modules, 'space_for_new_modules[]'),
                    (grounding_of_rectifiers, 'grounding_of_rectifier[]'),
                    (spd_in_rectifiers, 'spd_in_rectifier[]'),
                    (spd_models, 'spd_model[]'),
                    (total_installed_spds, 'total_installed_spds[]'),
                    (no_of_faulty_spds, 'no_of_faulty_spds[]')
                ]

                for lst, name in lists_to_check:
                    if len(lst) != expected_length:
                        raise ValueError(f"Mismatch in rectifier field lengths: {name} has {len(lst)} entries, expected {expected_length}")

                rectifiers_data = []
                for i in range(expected_length):
                    if not make_of_rectifiers[i].strip():
                        continue
                    grounding = grounding_of_rectifiers[i] if grounding_of_rectifiers[i] in valid_yes_no else None
                    spd = spd_in_rectifiers[i] if spd_in_rectifiers[i] in valid_yes_no else None
                    rectifier = {
                        'make_of_rectifier': make_of_rectifiers[i] or None,
                        'rectifier_capacity': safe_float(rectifier_capacities[i], 'rectifier_capacity') if rectifier_capacities[i].strip() else None,
                        'no_of_modules': safe_int(no_of_modules[i], 'no_of_modules') if no_of_modules[i].strip() else None,
                        'capacity_of_each_module': safe_float(capacity_of_each_module[i], 'capacity_of_each_module') if capacity_of_each_module[i].strip() else None,
                        'working_modules': safe_int(working_modules[i], 'working_modules') if working_modules[i].strip() else None,
                        'faulty_modules': safe_int(faulty_modules[i], 'faulty_modules') if faulty_modules[i].strip() else None,
                        'space_for_new_modules': safe_int(space_for_new_modules[i], 'space_for_new_modules') if space_for_new_modules[i].strip() else None,
                        'grounding_of_rectifier': grounding,
                        'spd_in_rectifier': spd,
                        'spd_model': spd_models[i] if spd_models[i].strip() else None,
                        'total_installed_spds': safe_int(total_installed_spds[i], 'total_installed_spds') if total_installed_spds[i].strip() else None,
                        'no_of_faulty_spds': safe_int(no_of_faulty_spds[i], 'no_of_faulty_spds') if no_of_faulty_spds[i].strip() else None
                    }
                    rectifiers_data.append(rectifier)
                general.power_info.wapda_ref_number = request.form.get('wapda_ref_number') or None
                general.power_info.transformer_capacity = request.form.get('transformer_capacity') or None
                general.power_info.transformer_earthing = request.form.get('transformer_earthing') or None
                general.power_info.working_status = request.form.get('working_status_power') or None
                general.power_info.name_of_nes_connected = request.form.get('name_of_nes_connected') or None
                general.power_info.load_of_individual_ne = safe_float(request.form.get('load_of_individual_ne'), 'load_of_individual_ne') if request.form.get('load_of_individual_ne') else None
                general.power_info.rectifiers = rectifiers_data if rectifiers_data else None
            else:
                general.power_info.wapda_ref_number = request.form.get('wapda_ref_number') or None
                general.power_info.transformer_capacity = request.form.get('transformer_capacity') or None
                general.power_info.transformer_earthing = request.form.get('transformer_earthing') or None
                general.power_info.working_status = request.form.get('working_status_power') or None
                general.power_info.name_of_nes_connected = request.form.get('name_of_nes_connected') or None
                general.power_info.load_of_individual_ne = safe_float(request.form.get('load_of_individual_ne'), 'load_of_individual_ne') if request.form.get('load_of_individual_ne') else None
                general.power_info.rectifiers = None
            general.power_info.updated_by = username
            general.power_info.updated_at = datetime.utcnow()

            # DG Information
            DGInformation.query.filter_by(general_id=general.sn).delete()
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

                for i in range(len(installed_dgs)):
                    if not installed_dgs[i].strip():
                        continue
                    dg_status = dg_statuses[i] if dg_statuses[i] in valid_dg_status else None
                    smart_switch = True if smart_switch_installeds[i].lower() == 'yes' else False if smart_switch_installeds[i].lower() == 'no' else None
                    ats = True if ats_installeds[i].lower() == 'yes' else False if ats_installeds[i].lower() == 'no' else None
                    dg = DGInformation(
                        general_id=general.sn,
                        installed_dg=installed_dgs[i] or None,
                        engine_make=engine_makes[i] if engine_makes[i].strip() else None,
                        installation_year=safe_int(installation_years[i], 'installation_year') if installation_years[i].strip() else None,
                        dg_status=dg_status,
                        dg_starting_battery=dg_starting_batteries[i] if dg_starting_batteries[i].strip() else None,
                        smart_switch_installed=smart_switch,
                        ats_installed=ats,
                        ats_capacity=ats_capacities[i] if ats_capacities[i].strip() else None,
                        name_of_faulty_ats_parts=name_of_faulty_ats_parts[i] if name_of_faulty_ats_parts[i].strip() else None,
                        no_of_faulty_ats_parts=safe_int(no_of_faulty_ats_parts[i], 'no_of_faulty_ats_parts') if no_of_faulty_ats_parts[i].strip() else None,
                        load_on_dg_p1=safe_float(load_on_dg_p1s[i], 'load_on_dg_p1') if load_on_dg_p1s[i].strip() else None,
                        load_on_dg_p2=safe_float(load_on_dg_p2s[i], 'load_on_dg_p2') if load_on_dg_p2s[i].strip() else None,
                        load_on_dg_p3=safe_float(load_on_dg_p3s[i], 'load_on_dg_p3') if load_on_dg_p3s[i].strip() else None,
                        site_load_total=safe_float(site_load_totals[i], 'site_load_total') if site_load_totals[i].strip() else None,
                        site_load_p1=safe_float(site_load_p1s[i], 'site_load_p1') if site_load_p1s[i].strip() else None,
                        site_load_p2=safe_float(site_load_p2s[i], 'site_load_p2') if site_load_p2s[i].strip() else None,
                        site_load_p3=safe_float(site_load_p3s[i], 'site_load_p3') if site_load_p3s[i].strip() else None,
                        created_by=username,
                        updated_by=username,
                        updated_at=datetime.utcnow()
                    )
                    db.session.add(dg)

            # Battery Bank Information
            # Archive existing battery banks before deleting
            existing_batteries = BatteryBank.query.filter_by(general_id=general.sn).all()
            for battery in existing_batteries:
                history_entry = BatteryBankHistory(
                    original_id=battery.id,
                    general_id=battery.general_id,
                    make_of_battery=battery.make_of_battery,
                    battery_capacity=battery.battery_capacity,
                    battery_type=battery.battery_type,
                    no_of_cells_bank=battery.no_of_cells_bank,
                    date_of_installation=battery.date_of_installation,
                    load_on_battery_bank=battery.load_on_battery_bank,
                    practical_backup_time=battery.practical_backup_time,
                    battery_installed_new_or_used=battery.battery_installed_new_or_used,
                    battery_moved_from=battery.battery_moved_from,
                    created_by=battery.created_by,
                    updated_by=username,
                    updated_at=battery.updated_at,
                    archived_at=datetime.utcnow()
                )
                db.session.add(history_entry)
            BatteryBank.query.filter_by(general_id=general.sn).delete()

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

                for i in range(len(make_of_batteries)):
                    if not make_of_batteries[i].strip():
                        continue
                    battery_type = battery_types[i] if battery_types[i] in valid_battery_types else None
                    battery_installation = battery_installed_new_or_useds[i] if battery_installed_new_or_useds[i] in valid_battery_installation else None
                    battery = BatteryBank(
                        general_id=general.sn,
                        make_of_battery=make_of_batteries[i] or None,
                        battery_capacity=safe_float(battery_capacities[i], 'battery_capacity') if battery_capacities[i].strip() else None,
                        battery_type=battery_type,
                        no_of_cells_bank=safe_int(no_of_cells_banks[i], 'no_of_cells_bank') if no_of_cells_banks[i].strip() else None,
                        date_of_installation=date_of_installations[i] if date_of_installations[i].strip() else None,
                        load_on_battery_bank=safe_float(load_on_battery_banks[i], 'load_on_battery_bank') if load_on_battery_banks[i].strip() else None,
                        practical_backup_time=safe_float(practical_backup_times[i], 'practical_backup_time') if practical_backup_times[i].strip() else None,
                        battery_installed_new_or_used=battery_installation,
                        battery_moved_from=battery_moved_froms[i] if battery_moved_froms[i].strip() else None,
                        created_by=username,
                        updated_by=username,
                        updated_at=datetime.utcnow()
                    )
                    db.session.add(battery)

            # AC Unit Information
            with db.session.no_autoflush:
                ACUnit.query.filter_by(general_id=general.sn).delete()
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
                            capacity_tons=safe_float(capacity_tons[i], 'capacity_tons') if capacity_tons[i].strip() else None,
                            type_of_ac=type_of_acs[i] if type_of_acs[i].strip() else None,
                            mount_type=mount_types[i] if mount_types[i].strip() else None,
                            date_of_installation=date_of_installation_acs[i] if date_of_installation_acs[i].strip() else None,
                            sequence_controller_installed=sequence_controller,
                            ac_load=safe_float(ac_loads[i], 'ac_load') if ac_loads[i].strip() else None,
                            total_ac_load=safe_float(total_ac_loads[i], 'total_ac_load') if total_ac_loads[i].strip() else None,
                            fault_nature_of_ac_unit=fault_nature_of_ac_units[i] if fault_nature_of_ac_units[i].strip() else None,
                            estimate_to_repair_ac=safe_float(estimate_to_repair_acs[i], 'estimate_to_repair_ac') if estimate_to_repair_acs[i].strip() else None,
                            created_by=username,
                            updated_by=username,
                            updated_at=datetime.utcnow()
                        )
                        db.session.add(ac_unit)

            # Solar Information
            if not general.solar_info:
                general.solar_info = SolarInformation(general_id=general.sn)
            general.solar_info.total_solar_size = safe_float(request.form.get('total_solar_size'), 'total_solar_size') if request.form.get('total_solar_size') else None
            general.solar_info.pv_solar_panel_capacity = safe_float(request.form.get('pv_solar_panel_capacity'), 'pv_solar_panel_capacity') if request.form.get('pv_solar_panel_capacity') else None
            general.solar_info.no_of_pv_panels_installed = safe_int(request.form.get('no_of_pv_panels_installed'), 'no_of_pv_panels_installed') if request.form.get('no_of_pv_panels_installed') else None
            general.solar_info.make_of_pv_panels = request.form.get('make_of_pv_panels') or None
            general.solar_info.charge_controller_make = request.form.get('charge_controller_make') or None
            general.solar_info.updated_by = username
            general.solar_info.updated_at = datetime.utcnow()

            # Colocation Information
            if not general.colocation_info:
                general.colocation_info = ColocationInformation(general_id=general.sn)
            colocation = request.form.get('colocation')
            general.colocation_info.colocation = colocation
            general.colocation_info.name_of_colocation_vendors = request.form.get('name_of_colocation_vendors') or None
            general.colocation_info.load_of_each_vendor = safe_float(request.form.get('load_of_each_vendor'), 'load_of_each_vendor') if request.form.get('load_of_each_vendor') else None
            general.colocation_info.total_load = safe_float(request.form.get('total_load'), 'total_load') if request.form.get('total_load') else None
            general.colocation_info.updated_by = username
            general.colocation_info.updated_at = datetime.utcnow()

            # Building Information
            if not general.building_info:
                general.building_info = BuildingInformation(general_id=general.sn)
            general.building_info.building_status = request.form.get('building_status') or None
            general.building_info.wall_doors_condition = request.form.get('wall_doors_condition') or None
            general.building_info.updated_by = username
            general.building_info.updated_at = datetime.utcnow()

            # Alarm Extension
            AlarmExtension.query.filter_by(general_id=general.sn).delete()
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
                        rectifier_failure=rectifier_failure,
                        created_by=username,
                        updated_by=username,
                        updated_at=datetime.utcnow()
                    )
                    db.session.add(alarm)

            # Earthing
            Earthing.query.filter_by(general_id=general.sn).delete()
            earthing_values = request.form.getlist('earthing_value[]')
            if earthing_values and earthing_values[0].strip():
                no_of_pits = request.form.getlist('no_of_pits[]')
                for i in range(len(earthing_values)):
                    if not earthing_values[i].strip():
                        continue
                    earthing = Earthing(
                        general_id=general.sn,
                        earthing_value=safe_float(earthing_values[i], 'earthing_value') if earthing_values[i].strip() else None,
                        no_of_pits=safe_int(no_of_pits[i], 'no_of_pits') if no_of_pits[i].strip() else None,
                        created_by=username,
                        updated_by=username,
                        updated_at=datetime.utcnow()
                    )
                    db.session.add(earthing)

            # Fire Extinguishers
            FireExtinguisher.query.filter_by(general_id=general.sn).delete()
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
                        no_of_fes=safe_int(no_of_fes[i], 'no_of_fes') if no_of_fes[i].strip() else None,
                        type_of_gas=type_of_gases[i] if type_of_gases[i].strip() else None,
                        date_of_expiry=date_of_expiries[i] if date_of_expiries[i].strip() else None,
                        created_by=username,
                        updated_by=username,
                        updated_at=datetime.utcnow()
                    )
                    db.session.add(fire_ext)

            # PMR Information
            # Archive existing PMR entries before deleting
            existing_pmrs = PMRInformation.query.filter_by(general_id=general.sn).all()
            for pmr in existing_pmrs:
                history_entry = PMRInformationHistory(
                    original_id=pmr.id,
                    general_id=pmr.general_id,
                    pmr_performed=pmr.pmr_performed,
                    last_performed_date=pmr.last_performed_date,
                    created_by=pmr.created_by,
                    updated_by=username,
                    updated_at=pmr.updated_at,
                    archived_at=datetime.utcnow()
                )
                db.session.add(history_entry)
            PMRInformation.query.filter_by(general_id=general.sn).delete()

            pmr_performed = request.form.get('pmr_performed')
            last_performed_date = request.form.get('last_performed_date') or None
            if pmr_performed and pmr_performed.strip():
                pmr_performed = pmr_performed if pmr_performed in valid_yes_no else None
                last_performed_date = last_performed_date if pmr_performed == 'Yes' and last_performed_date.strip() else None
                pmr = PMRInformation(
                    general_id=general.sn,
                    pmr_performed=pmr_performed,
                    last_performed_date=last_performed_date,
                    created_by=username,
                    updated_by=username,
                    updated_at=datetime.utcnow()
                )
                db.session.add(pmr)

            db.session.commit()
            flash('Exchange updated successfully!', 'success')
            logging.info(f"User {username} updated exchange SN {sn}")
            return redirect(url_for('index'))

        except ValueError as e:
            db.session.rollback()
            flash(str(e), 'error')
            logging.error(f"Validation error updating exchange SN {sn} by {username}: {str(e)}")
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating exchange: {str(e)}", 'error')
            logging.error(f"Error updating exchange SN {sn} by {username}: {str(e)}")

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
        logging.info("Starting export process...")
        user_region = session.get('region')
        if user_region == "All":
            exchanges = GeneralInformation.query.limit(500).all()
        else:
            exchanges = GeneralInformation.query.filter_by(domain=user_region).limit(500).all()

        if not exchanges:
            flash('No exchanges found to export.')
            logging.warning("No exchanges found for export.")
            return redirect(url_for('index'))

        total_exchanges = GeneralInformation.query.count()
        if total_exchanges > 500:
            flash('Export limited to 500 records. Please contact support for a full export.')
            logging.info(f"Total exchanges: {total_exchanges}, limited to 500 for export.")

        logging.info(f"Processing {len(exchanges)} exchanges for export.")

        max_towers = max((len(exchange.towers) for exchange in exchanges if exchange.towers), default=0)
        max_dgs = max((len(exchange.dgs) for exchange in exchanges if exchange.dgs), default=0)
        max_batteries = max((len(exchange.battery_banks) for exchange in exchanges if exchange.battery_banks), default=0)
        max_acs = max((len(exchange.ac_units) for exchange in exchanges if exchange.ac_units), default=0)
        max_alarms = max((len(exchange.alarms) for exchange in exchanges if exchange.alarms), default=0)
        max_earthings = max((len(exchange.earthings) for exchange in exchanges if exchange.earthings), default=0)
        max_fire_extinguishers = max((len(exchange.fire_extinguishers) for exchange in exchanges if exchange.fire_extinguishers), default=0)
        max_pmrs = max((len(exchange.pmr_infos) for exchange in exchanges if exchange.pmr_infos), default=0)
        max_rectifiers = max((len(exchange.power_info.rectifiers) if exchange.power_info and exchange.power_info.rectifiers else 0 for exchange in exchanges), default=0)

        data = []
        for idx, exchange in enumerate(exchanges):
            try:
                row = {
                    'SN': getattr(exchange, 'sn', None),
                    'Region': getattr(exchange, 'region', None),
                    'Domain': getattr(exchange, 'domain', None),
                    'Exchange Name': getattr(exchange, 'site_name', None),
                    'Exchange LIC': getattr(exchange, 'site_lic', None),
                    'FLC': getattr(exchange, 'flc', None),
                    'Site Category': getattr(exchange, 'site_category', None),
                    'NEs Installed (Complete Detail)': getattr(exchange, 'nes_installed', None),
                    'Latitude': getattr(exchange, 'latitude', None),
                    'Longitude': getattr(exchange, 'longitude', None),
                    'Tower Available (Y/N)': getattr(exchange, 'tower_available', None)
                }
                for i in range(max_towers):
                    tower = exchange.towers[i] if i < len(exchange.towers) else None
                    row[f'Type and Height of Tower {i+1}'] = getattr(tower, 'tower_type_height', None) if tower else None

                power_info = getattr(exchange, 'power_info', None)
                if power_info:
                    row.update({
                        'WAPDA Ref Number': getattr(power_info, 'wapda_ref_number', None),
                        'Transformer Capacity': getattr(power_info, 'transformer_capacity', None),
                        'Transformer Earthing': getattr(power_info, 'transformer_earthing', None),
                        'Working Status': getattr(power_info, 'working_status', None),
                        'Name of NEs Connected': getattr(power_info, 'name_of_nes_connected', None),
                        'Load of Individual NE': getattr(power_info, 'load_of_individual_ne', None),
                    })
                else:
                    row.update({
                        'WAPDA Ref Number': None,
                        'Transformer Capacity': None,
                        'Transformer Earthing': None,
                        'Working Status': None,
                        'Name of NEs Connected': None,
                        'Load of Individual NE': None,
                    })

                for i in range(max_dgs):
                    dg = exchange.dgs[i] if i < len(exchange.dgs) else None
                    row.update({
                        f'Installed DGs {i+1}': getattr(dg, 'installed_dg', None) if dg else None,
                        f'Engine Make {i+1}': getattr(dg, 'engine_make', None) if dg else None,
                        f'Installation Year {i+1}': getattr(dg, 'installation_year', None) if dg else None,
                        f'DG Status {i+1}': getattr(dg, 'dg_status', None) if dg else None,
                        f'DG Starting Battery {i+1}': getattr(dg, 'dg_starting_battery', None) if dg else None,
                        f'Smart Switch Installed {i+1} (Y/N)': getattr(dg, 'smart_switch_installed', None) if dg else None,
                        f'ATS Installed {i+1} (Y/N)': getattr(dg, 'ats_installed', None) if dg else None,
                        f'ATS Capacity {i+1}': getattr(dg, 'ats_capacity', None) if dg else None,
                        f'Name of Faulty ATS Parts {i+1} (SS,Relays,Contactor etc)': getattr(dg, 'name_of_faulty_ats_parts', None) if dg else None,
                        f'No of Faulty ATS Parts {i+1}': getattr(dg, 'no_of_faulty_ats_parts', None) if dg else None,
                        f'Load on DG P1 {i+1}': getattr(dg, 'load_on_dg_p1', None) if dg else None,
                        f'Load on DG P2 {i+1}': getattr(dg, 'load_on_dg_p2', None) if dg else None,
                        f'Load on DG P3 {i+1}': getattr(dg, 'load_on_dg_p3', None) if dg else None,
                        f'Site Load Total {i+1}': getattr(dg, 'site_load_total', None) if dg else None,
                        f'Site Load P1 {i+1}': getattr(dg, 'site_load_p1', None) if dg else None,
                        f'Site Load P2 {i+1}': getattr(dg, 'site_load_p2', None) if dg else None,
                        f'Site Load P3 {i+1}': getattr(dg, 'site_load_p3', None) if dg else None,
                    })

                rectifiers = getattr(power_info, 'rectifiers', []) if power_info else []
                for i in range(max_rectifiers):
                    rectifier = rectifiers[i] if i < len(rectifiers) else None
                    row.update({
                        f'Make of Rectifier {i+1}': rectifier.get('make_of_rectifier') if rectifier else None,
                        f'Rectifier Capacity {i+1} (A)': rectifier.get('rectifier_capacity') if rectifier else None,
                        f'No. of Modules {i+1}': rectifier.get('no_of_modules') if rectifier else None,
                        f'Capacity of Each Module {i+1} (A)': rectifier.get('capacity_of_each_module') if rectifier else None,
                        f'Working Modules {i+1} (No.)': rectifier.get('working_modules') if rectifier else None,
                        f'Faulty Modules {i+1} (No.)': rectifier.get('faulty_modules') if rectifier else None,
                        f'Space for New Modules {i+1} (No.)': rectifier.get('space_for_new_modules') if rectifier else None,
                        f'Grounding of Rectifier {i+1} (Y/N)': rectifier.get('grounding_of_rectifier') if rectifier else None,
                        f'SPD in Rectifier {i+1} (Y/N)': rectifier.get('spd_in_rectifier') if rectifier else None,
                        f'SPD Model {i+1} (V and A Rating)': rectifier.get('spd_model') if rectifier else None,
                        f'Total Installed SPDs {i+1}': rectifier.get('total_installed_spds') if rectifier else None,
                        f'No of Faulty SPDs {i+1}': rectifier.get('no_of_faulty_spds') if rectifier else None,
                    })

                for i in range(max_batteries):
                    battery = exchange.battery_banks[i] if i < len(exchange.battery_banks) else None
                    row.update({
                        f'Make of Battery {i+1}': getattr(battery, 'make_of_battery', None) if battery else None,
                        f'Battery Capacity {i+1} (AH)': getattr(battery, 'battery_capacity', None) if battery else None,
                        f'Battery Type {i+1} (2V/12V)': getattr(battery, 'battery_type', None) if battery else None,
                        f'No. of Cells/Bank {i+1}': getattr(battery, 'no_of_cells_bank', None) if battery else None,
                        f'Date of Installation {i+1}': getattr(battery, 'date_of_installation', None) if battery else None,
                        f'Load on Battery Bank {i+1} (A)': getattr(battery, 'load_on_battery_bank', None) if battery else None,
                        f'Practical Backup Time {i+1} (Hrs)': getattr(battery, 'practical_backup_time', None) if battery else None,
                        f'Battery Installed {i+1} New or Used': getattr(battery, 'battery_installed_new_or_used', None) if battery else None,
                        f'Battery Moved From {i+1} (Incase Used Installed)': getattr(battery, 'battery_moved_from', None) if battery else None,
                    })

                for i in range(max_acs):
                    ac = exchange.ac_units[i] if i < len(exchange.ac_units) else None
                    row.update({
                        f'Location of AC Unit {i+1}': getattr(ac, 'location_of_ac_unit', None) if ac else None,
                        f'Working Status of AC {i+1} (Working/Faulty/Spare)': getattr(ac, 'working_status', None) if ac else None,
                        f'AC Make {i+1}': getattr(ac, 'ac_make', None) if ac else None,
                        f'Capacity {i+1} (Tons)': getattr(ac, 'capacity_tons', None) if ac else None,
                        f'Type of AC {i+1}': getattr(ac, 'type_of_ac', None) if ac else None,
                        f'Mount Type {i+1}': getattr(ac, 'mount_type', None) if ac else None,
                        f'Date of Installation AC {i+1}': getattr(ac, 'date_of_installation', None) if ac else None,
                        f'Sequence Controller Installed {i+1} (Y/N)': getattr(ac, 'sequence_controller_installed', None) if ac else None,
                        f'AC Load {i+1}': getattr(ac, 'ac_load', None) if ac else None,
                        f'Total AC Load {i+1}': getattr(ac, 'total_ac_load', None) if ac else None,
                        f'Fault Nature of AC Unit {i+1}': getattr(ac, 'fault_nature_of_ac_unit', None) if ac else None,
                        f'Estimate to Repair AC {i+1}': getattr(ac, 'estimate_to_repair_ac', None) if ac else None,
                    })

                solar_info = getattr(exchange, 'solar_info', None)
                if solar_info:
                    row.update({
                        'Total Solar Size (KW)': getattr(solar_info, 'total_solar_size', None),
                        'PV Solar Panel Capacity (W)': getattr(solar_info, 'pv_solar_panel_capacity', None),
                        'No. of PV Panels Installed': getattr(solar_info, 'no_of_pv_panels_installed', None),
                        'Make of PV Panels': getattr(solar_info, 'make_of_pv_panels', None),
                        'Charge Controller Make': getattr(solar_info, 'charge_controller_make', None),
                    })
                else:
                    row.update({
                        'Total Solar Size (KW)': None,
                        'PV Solar Panel Capacity (W)': None,
                        'No. of PV Panels Installed': None,
                        'Make of PV Panels': None,
                        'Charge Controller Make': None,
                    })

                for i in range(max_earthings):
                    earthing = exchange.earthings[i] if i < len(exchange.earthings) else None
                    row.update({
                        f'Earthing Value {i+1}': getattr(earthing, 'earthing_value', None) if earthing else None,
                        f'No. of Pits {i+1}': getattr(earthing, 'no_of_pits', None) if earthing else None,
                    })

                for i in range(max_fire_extinguishers):
                    fire_ext = exchange.fire_extinguishers[i] if i < len(exchange.fire_extinguishers) else None
                    row.update({
                        f'FE Installed {i+1}': getattr(fire_ext, 'fe_installed', None) if fire_ext else None,
                        f'No. of FEs {i+1}': getattr(fire_ext, 'no_of_fes', None) if fire_ext else None,
                        f'Type of Gas {i+1}': getattr(fire_ext, 'type_of_gas', None) if fire_ext else None,
                        f'Date of Expiry {i+1}': getattr(fire_ext, 'date_of_expiry', None) if fire_ext else None,
                    })

                for i in range(max_pmrs):
                    pmr = exchange.pmr_infos[i] if i < len(exchange.pmr_infos) else None
                    row.update({
                        f'PMR Performed {i+1} (Y/N)': getattr(pmr, 'pmr_performed', None) if pmr else None,
                        f'Last Performed Date {i+1}': getattr(pmr, 'last_performed_date', None) if pmr else None,
                    })

                for i in range(max_alarms):
                    alarm = exchange.alarms[i] if i < len(exchange.alarms) else None
                    row.update({
                        f'AC Main Failure {i+1} (Y/N)': getattr(alarm, 'ac_main_failure', None) if alarm else None,
                        f'DC Low Voltages {i+1} (Y/N)': getattr(alarm, 'dc_low_voltages', None) if alarm else None,
                        f'Rectifier Failure {i+1} (Y/N)': getattr(alarm, 'rectifier_failure', None) if alarm else None,
                    })

                colocation_info = getattr(exchange, 'colocation_info', None)
                if colocation_info:
                    row.update({
                        'Colocation (Y/N)': getattr(colocation_info, 'colocation', None),
                        'Name of Colocation Vendors': getattr(colocation_info, 'name_of_colocation_vendors', None),
                        'Load of Each Vendor': getattr(colocation_info, 'load_of_each_vendor', None),
                        'Total Load': getattr(colocation_info, 'total_load', None),
                    })
                else:
                    row.update({
                        'Colocation (Y/N)': None,
                        'Name of Colocation Vendors': None,
                        'Load of Each Vendor': None,
                        'Total Load': None,
                    })

                building_info = getattr(exchange, 'building_info', None)
                if building_info:
                    row.update({
                        'Building Status (Good/Poor/Worst)': getattr(building_info, 'building_status', None),
                        'Wall/Doors Condition': getattr(building_info, 'wall_doors_condition', None),
                    })
                else:
                    row.update({
                        'Building Status (Good/Poor/Worst)': None,
                        'Wall/Doors Condition': None,
                    })

                data.append(row)
            except Exception as e:
                logging.error(f"Error processing exchange {idx + 1}: {str(e)}")
                continue

        if not data:
            flash('No data available to export after processing.')
            logging.warning("No data available to export after processing.")
            return redirect(url_for('index'))

        logging.info(f"Processed {len(data)} rows of data.")

        general_info_headers = ['SN', 'Region', 'Domain', 'Exchange Name', 'Exchange LIC', 'FLC', 'Site Category', 'NEs Installed (Complete Detail)', 'Latitude', 'Longitude', 'Tower Available (Y/N)'] + [f'Type and Height of Tower {i+1}' for i in range(max_towers)]
        power_headers = ['WAPDA Ref Number', 'Transformer Capacity', 'Transformer Earthing', 'Working Status', 'Name of NEs Connected', 'Load of Individual NE'] + \
                       [f'Installed DGs {i+1}' for i in range(max_dgs)] + \
                       [f'Engine Make {i+1}' for i in range(max_dgs)] + \
                       [f'Installation Year {i+1}' for i in range(max_dgs)] + \
                       [f'DG Status {i+1}' for i in range(max_dgs)] + \
                       [f'DG Starting Battery {i+1}' for i in range(max_dgs)] + \
                       [f'Smart Switch Installed {i+1} (Y/N)' for i in range(max_dgs)] + \
                       [f'ATS Installed {i+1} (Y/N)' for i in range(max_dgs)] + \
                       [f'ATS Capacity {i+1}' for i in range(max_dgs)] + \
                       [f'Name of Faulty ATS Parts {i+1} (SS,Relays,Contactor etc)' for i in range(max_dgs)] + \
                       [f'No of Faulty ATS Parts {i+1}' for i in range(max_dgs)] + \
                       [f'Load on DG P1 {i+1}' for i in range(max_dgs)] + \
                       [f'Load on DG P2 {i+1}' for i in range(max_dgs)] + \
                       [f'Load on DG P3 {i+1}' for i in range(max_dgs)] + \
                       [f'Site Load Total {i+1}' for i in range(max_dgs)] + \
                       [f'Site Load P1 {i+1}' for i in range(max_dgs)] + \
                       [f'Site Load P2 {i+1}' for i in range(max_dgs)] + \
                       [f'Site Load P3 {i+1}' for i in range(max_dgs)] + \
                       [f'Make of Rectifier {i+1}' for i in range(max_rectifiers)] + \
                       [f'Rectifier Capacity {i+1} (A)' for i in range(max_rectifiers)] + \
                       [f'No. of Modules {i+1}' for i in range(max_rectifiers)] + \
                       [f'Capacity of Each Module {i+1} (A)' for i in range(max_rectifiers)] + \
                       [f'Working Modules {i+1} (No.)' for i in range(max_rectifiers)] + \
                       [f'Faulty Modules {i+1} (No.)' for i in range(max_rectifiers)] + \
                       [f'Space for New Modules {i+1} (No.)' for i in range(max_rectifiers)] + \
                       [f'Grounding of Rectifier {i+1} (Y/N)' for i in range(max_rectifiers)] + \
                       [f'SPD in Rectifier {i+1} (Y/N)' for i in range(max_rectifiers)] + \
                       [f'SPD Model {i+1} (V and A Rating)' for i in range(max_rectifiers)] + \
                       [f'Total Installed SPDs {i+1}' for i in range(max_rectifiers)] + \
                       [f'No of Faulty SPDs {i+1}' for i in range(max_rectifiers)]
        battery_headers = [f'Make of Battery {i+1}' for i in range(max_batteries)] + \
                         [f'Battery Capacity {i+1} (AH)' for i in range(max_batteries)] + \
                         [f'Battery Type {i+1} (2V/12V)' for i in range(max_batteries)] + \
                         [f'No. of Cells/Bank {i+1}' for i in range(max_batteries)] + \
                         [f'Date of Installation {i+1}' for i in range(max_batteries)] + \
                         [f'Load on Battery Bank {i+1} (A)' for i in range(max_batteries)] + \
                         [f'Practical Backup Time {i+1} (Hrs)' for i in range(max_batteries)] + \
                         [f'Battery Installed {i+1} New or Used' for i in range(max_batteries)] + \
                         [f'Battery Moved From {i+1} (Incase Used Installed)' for i in range(max_batteries)]
        ac_headers = [f'Location of AC Unit {i+1}' for i in range(max_acs)] + \
                    [f'Working Status of AC {i+1} (Working/Faulty/Spare)' for i in range(max_acs)] + \
                    [f'AC Make {i+1}' for i in range(max_acs)] + \
                    [f'Capacity {i+1} (Tons)' for i in range(max_acs)] + \
                    [f'Type of AC {i+1}' for i in range(max_acs)] + \
                    [f'Mount Type {i+1}' for i in range(max_acs)] + \
                    [f'Date of Installation AC {i+1}' for i in range(max_acs)] + \
                    [f'Sequence Controller Installed {i+1} (Y/N)' for i in range(max_acs)] + \
                    [f'AC Load {i+1}' for i in range(max_acs)] + \
                    [f'Total AC Load {i+1}' for i in range(max_acs)] + \
                    [f'Fault Nature of AC Unit {i+1}' for i in range(max_acs)] + \
                    [f'Estimate to Repair AC {i+1}' for i in range(max_acs)]
        solar_headers = ['Total Solar Size (KW)', 'PV Solar Panel Capacity (W)', 'No. of PV Panels Installed', 'Make of PV Panels', 'Charge Controller Make']
        earthing_headers = [f'Earthing Value {i+1}' for i in range(max_earthings)] + \
                          [f'No. of Pits {i+1}' for i in range(max_earthings)]
        fire_ext_headers = [f'FE Installed {i+1}' for i in range(max_fire_extinguishers)] + \
                          [f'No. of FEs {i+1}' for i in range(max_fire_extinguishers)] + \
                          [f'Type of Gas {i+1}' for i in range(max_fire_extinguishers)] + \
                          [f'Date of Expiry {i+1}' for i in range(max_fire_extinguishers)]
        pmr_headers = [f'PMR Performed {i+1} (Y/N)' for i in range(max_pmrs)] + \
                     [f'Last Performed Date {i+1}' for i in range(max_pmrs)]
        alarm_headers = [f'AC Main Failure {i+1} (Y/N)' for i in range(max_alarms)] + \
                       [f'DC Low Voltages {i+1} (Y/N)' for i in range(max_alarms)] + \
                       [f'Rectifier Failure {i+1} (Y/N)' for i in range(max_alarms)]
        colocation_headers = ['Colocation (Y/N)', 'Name of Colocation Vendors', 'Load of Each Vendor', 'Total Load']
        building_headers = ['Building Status (Good/Poor/Worst)', 'Wall/Doors Condition']

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            workbook = writer.book
            worksheet = workbook.add_worksheet('Exchanges')

            # Define formats
            header_format = workbook.add_format({'bg_color': '#4BACC6', 'font_color': 'white', 'bold': True, 'border': 1})
            general_info_format = workbook.add_format({'bg_color': '#D3D3D3', 'border': 1})
            power_info_format = workbook.add_format({'bg_color': '#ADD8E6', 'border': 1})
            battery_format = workbook.add_format({'bg_color': '#90EE90', 'border': 1})
            ac_format = workbook.add_format({'bg_color': '#FFB6C1', 'border': 1})
            solar_format = workbook.add_format({'bg_color': '#FFD700', 'border': 1})
            earthing_format = workbook.add_format({'bg_color': '#DDA0DD', 'border': 1})
            fire_ext_format = workbook.add_format({'bg_color': '#FFA07A', 'border': 1})
            pmr_format = workbook.add_format({'bg_color': '#98FB98', 'border': 1})
            alarm_format = workbook.add_format({'bg_color': '#B0C4DE', 'border': 1})
            colocation_format = workbook.add_format({'bg_color': '#F0E68C', 'border': 1})
            building_format = workbook.add_format({'bg_color': '#E6E6FA', 'border': 1})

            sections = [
                ("General Information", general_info_headers, general_info_format),
                ("Power Information", power_headers, power_info_format),
                ("Battery Bank Information", battery_headers, battery_format),
                ("AC Units Information", ac_headers, ac_format),
                ("Installed Solar Information", solar_headers, solar_format),
                ("Earthing", earthing_headers, earthing_format),
                ("Fire Extinguishers", fire_ext_headers, fire_ext_format),
                ("PMR Information", pmr_headers, pmr_format),
                ("Alarm Extension", alarm_headers, alarm_format),
                ("Colocation Information", colocation_headers, colocation_format),
                ("Building Information", building_headers, building_format)
            ]

            sections = [(title, headers, fmt) for title, headers, fmt in sections if headers]

            all_headers = []
            for _, headers, _ in sections:
                all_headers.extend(headers)

            col = 0
            for section_title, section_headers, section_format in sections:
                if not section_headers:
                    continue
                start_col = col
                end_col = col + len(section_headers) - 1
                worksheet.merge_range(0, start_col, 0, end_col, section_title, header_format)
                worksheet.write_row(1, col, section_headers, section_format)
                col = end_col + 1

            df = pd.DataFrame(data)
            df = df[all_headers]
            # Replace NaN and inf with None to avoid xlsxwriter errors
            df = df.replace([float('nan'), float('inf'), -float('inf')], None)

            for idx, row in df.iterrows():
                worksheet.write_row(idx + 2, 0, row.tolist())

            for idx, header in enumerate(all_headers):
                max_len = max((len(str(df[header].iloc[i])) for i in range(len(df)) if pd.notna(df[header].iloc[i])) + [len(header) + 2])
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
        logging.error(f"Error exporting data: {str(e)}", exc_info=True)
        return redirect(url_for('index'))
        
@app.route('/view_exchanges')
@login_required
def view_exchanges():
    user_region = session.get('region')
    if user_region == "All":
        exchanges = GeneralInformation.query.all()
    else:
        exchanges = GeneralInformation.query.filter_by(domain=user_region).all()

    # Prepare data for the template
    exchange_data = []
    for exchange in exchanges:
        # Fetch the latest battery history
        latest_battery = BatteryBankHistory.query.filter_by(general_id=exchange.sn)\
            .order_by(BatteryBankHistory.archived_at.desc()).first()
        
        # Fetch the latest PMR history
        latest_pmr = PMRInformationHistory.query.filter_by(general_id=exchange.sn)\
            .order_by(PMRInformationHistory.archived_at.desc()).first()

        # Create a dictionary with all necessary data
        exchange_info = {
            'sn': exchange.sn,
            'region': exchange.region,
            'domain': exchange.domain,
            'site_name': exchange.site_name,
            'created_by': exchange.created_by,
            'updated_by': exchange.updated_by,
            'updated_at': exchange.updated_at,
            'latest_battery': latest_battery,
            'latest_pmr': latest_pmr
        }
        exchange_data.append(exchange_info)

    return render_template('view_exchanges.html', exchanges=exchange_data)
    
@app.route('/filters', methods=['GET', 'POST'])
@login_required
def filters():
    user_region = session.get('region')
    logger.debug(f"User region from session: {user_region}")

    # Get available filter options based on user's unlocked regions
    if user_region == "All":
        available_domains_query = db.session.query(GeneralInformation.domain).distinct().all()
        available_categories_query = db.session.query(GeneralInformation.site_category).distinct().all()
    else:
        available_domains_query = db.session.query(GeneralInformation.domain).filter_by(region=user_region).distinct().all()
        available_categories_query = db.session.query(GeneralInformation.site_category).filter_by(region=user_region).distinct().all()
    available_domains = [d[0] for d in available_domains_query if d[0] is not None]
    available_categories = [c[0] for c in available_categories_query if c[0] is not None]
    logger.debug(f"Available domains: {available_domains}")
    logger.debug(f"Available categories: {available_categories}")

    # Initialize filters from session
    domain_filter = session.get('domain_filter', '')
    category_filter = session.get('category_filter', '')

    # Apply filters only if the form is submitted (POST request)
    if request.method == 'POST':
        domain_filter = request.form.get('domain_filter', '')
        category_filter = request.form.get('category_filter', '')

        # Update session with new filter values
        session['domain_filter'] = domain_filter
        session['category_filter'] = category_filter

        # Handle form actions
        if 'clear_filters' in request.form:
            session.pop('domain_filter', None)
            session.pop('category_filter', None)
            domain_filter = ''
            category_filter = ''
            return redirect(url_for('filters'))

    # Fetch data based on region and applied filters
    query = GeneralInformation.query
    if user_region != "All":
        query = query.filter_by(region=user_region)
    if domain_filter and domain_filter in available_domains:
        query = query.filter_by(domain=domain_filter)
    if category_filter and category_filter in available_categories:
        query = query.filter_by(site_category=category_filter)

    exchanges = query.all()
    logger.debug(f"Number of exchanges fetched: {len(exchanges)}")

    # Prepare data for the table by flattening all sections
    table_data = []
    for exchange in exchanges:
        row = {}
        # General Information
        row['SN'] = exchange.sn
        row['Region'] = exchange.region
        row['Domain'] = exchange.domain
        row['Site Name'] = exchange.site_name
        row['Site LIC'] = exchange.site_lic
        row['FLC'] = exchange.flc
        row['Site Category'] = exchange.site_category
        row['NEs Installed'] = exchange.nes_installed
        row['Latitude'] = exchange.latitude
        row['Longitude'] = exchange.longitude
        row['Tower Available'] = exchange.tower_available
        row['Towers'] = [tower.tower_type_height for tower in exchange.towers] if exchange.towers else []

        # Power Information
        power_info = exchange.power_info
        if power_info and power_info.rectifiers is not None:
            row['Power Info'] = {
                'WAPDA Ref Number': power_info.wapda_ref_number,
                'Transformer Capacity': power_info.transformer_capacity,
                'Transformer Earthing': power_info.transformer_earthing,
                'Working Status': power_info.working_status,
                'Name of NEs Connected': power_info.name_of_nes_connected,
                'Load of Individual NE': power_info.load_of_individual_ne,
                'Rectifiers': power_info.rectifiers
            }
        else:
            row['Power Info'] = {
                'WAPDA Ref Number': None,
                'Transformer Capacity': None,
                'Transformer Earthing': None,
                'Working Status': None,
                'Name of NEs Connected': None,
                'Load of Individual NE': None,
                'Rectifiers': []
            }

        # DGs
        row['DGs'] = [{k: v for k, v in dg.__dict__.items() if not k.startswith('_')} for dg in exchange.dgs] if exchange.dgs else []

        # Battery Banks
        row['Battery Banks'] = [{k: v for k, v in bb.__dict__.items() if not k.startswith('_')} for bb in exchange.battery_banks] if exchange.battery_banks else []

        # AC Units
        row['AC Units'] = [{k: v for k, v in ac.__dict__.items() if not k.startswith('_')} for ac in exchange.ac_units] if exchange.ac_units else []

        # Solar Info
        row['Solar Info'] = {
            'Total Solar Size': exchange.solar_info.total_solar_size if exchange.solar_info else None,
            'PV Solar Panel Capacity': exchange.solar_info.pv_solar_panel_capacity if exchange.solar_info else None,
            'No of PV Panels Installed': exchange.solar_info.no_of_pv_panels_installed if exchange.solar_info else None,
            'Make of PV Panels': exchange.solar_info.make_of_pv_panels if exchange.solar_info else None,
            'Charge Controller Make': exchange.solar_info.charge_controller_make if exchange.solar_info else None
        } if exchange.solar_info else {}

        # Colocation Info
        row['Colocation Info'] = {
            'Colocation': exchange.colocation_info.colocation if exchange.colocation_info else None,
            'Name of Colocation Vendors': exchange.colocation_info.name_of_colocation_vendors if exchange.colocation_info else None,
            'Load of Each Vendor': exchange.colocation_info.load_of_each_vendor if exchange.colocation_info else None,
            'Total Load': exchange.colocation_info.total_load if exchange.colocation_info else None
        } if exchange.colocation_info else {}

        # Building Info
        row['Building Info'] = {
            'Building Status': exchange.building_info.building_status if exchange.building_info else None,
            'Wall/Doors Condition': exchange.building_info.wall_doors_condition if exchange.building_info else None
        } if exchange.building_info else {}

        # Alarms
        row['Alarms'] = [{k: v for k, v in alarm.__dict__.items() if not k.startswith('_')} for alarm in exchange.alarms] if exchange.alarms else []

        # Earthings
        row['Earthings'] = [{k: v for k, v in earthing.__dict__.items() if not k.startswith('_')} for earthing in exchange.earthings] if exchange.earthings else []

        # Fire Extinguishers
        row['Fire Extinguishers'] = [{k: v for k, v in fe.__dict__.items() if not k.startswith('_')} for fe in exchange.fire_extinguishers] if exchange.fire_extinguishers else []

        # PMR Infos
        row['PMR Infos'] = [{k: v for k, v in pmr.__dict__.items() if not k.startswith('_')} for pmr in exchange.pmr_infos] if exchange.pmr_infos else []

        table_data.append(row)

    logger.debug(f"Table data length: {len(table_data)}")

    # Calculate the maximum number of rectifiers across all exchanges
    max_rectifiers = 0
    for exchange in exchanges:
        power_info = exchange.power_info
        if power_info and power_info.rectifiers is not None:
            rectifier_count = len(power_info.rectifiers)
            max_rectifiers = max(max_rectifiers, rectifier_count)
    max_rectifiers = max(max_rectifiers, 1)  # Ensure at least 1 to avoid empty loops in the template
    logger.debug(f"Calculated max_rectifiers: {max_rectifiers}")

    # Calculate maximum counts for other sections to ensure proper column alignment
    max_dgs = max(len(row['DGs']) for row in table_data) if table_data else 0
    max_dgs = max(max_dgs, 1)
    max_battery_banks = max(len(row['Battery Banks']) for row in table_data) if table_data else 0
    max_battery_banks = max(max_battery_banks, 1)
    max_ac_units = max(len(row['AC Units']) for row in table_data) if table_data else 0
    max_ac_units = max(max_ac_units, 1)
    max_alarms = max(len(row['Alarms']) for row in table_data) if table_data else 0
    max_alarms = max(max_alarms, 1)
    max_earthings = max(len(row['Earthings']) for row in table_data) if table_data else 0
    max_earthings = max(max_earthings, 1)
    max_fire_extinguishers = max(len(row['Fire Extinguishers']) for row in table_data) if table_data else 0
    max_fire_extinguishers = max(max_fire_extinguishers, 1)
    max_pmr_infos = max(len(row['PMR Infos']) for row in table_data) if table_data else 0
    max_pmr_infos = max(max_pmr_infos, 1)
    max_towers = max(len(row['Towers']) for row in table_data) if table_data else 0
    max_towers = max(max_towers, 1)

    # Handle export action
    if request.method == 'POST' and 'export_filtered' in request.form:
        # Flatten the table_data for export
        export_data = []
        for row in table_data:
            export_row = {}
            # Flatten General Information
            export_row['SN'] = row['SN']
            export_row['Region'] = row['Region']
            export_row['Domain'] = row['Domain']
            export_row['Site Name'] = row['Site Name']
            export_row['Site LIC'] = row['Site LIC']
            export_row['FLC'] = row['FLC']
            export_row['Site Category'] = row['Site Category']
            export_row['NEs Installed'] = row['NEs Installed']
            export_row['Latitude'] = row['Latitude']
            export_row['Longitude'] = row['Longitude']
            export_row['Tower Available'] = row['Tower Available']
            for i in range(max_towers):
                export_row[f'Tower {i+1} Type/Height'] = row['Towers'][i] if i < len(row['Towers']) else None

            # Flatten Power Information
            export_row['WAPDA Ref Number'] = row['Power Info']['WAPDA Ref Number']
            export_row['Transformer Capacity'] = row['Power Info']['Transformer Capacity']
            export_row['Transformer Earthing'] = row['Power Info']['Transformer Earthing']
            export_row['Working Status (Power)'] = row['Power Info']['Working Status']
            export_row['Name of NEs Connected'] = row['Power Info']['Name of NEs Connected']
            export_row['Load of Individual NE'] = row['Power Info']['Load of Individual NE']
            for i in range(max_rectifiers):
                rectifier = row['Power Info']['Rectifiers'][i] if i < len(row['Power Info']['Rectifiers']) else None
                export_row[f'Rectifier {i+1} Make'] = rectifier.get('make_of_rectifier') if rectifier else None
                export_row[f'Rectifier {i+1} Capacity'] = rectifier.get('rectifier_capacity') if rectifier else None
                export_row[f'Rectifier {i+1} No of Modules'] = rectifier.get('no_of_modules') if rectifier else None
                export_row[f'Rectifier {i+1} Capacity of Each Module'] = rectifier.get('capacity_of_each_module') if rectifier else None
                export_row[f'Rectifier {i+1} Working Modules'] = rectifier.get('working_modules') if rectifier else None
                export_row[f'Rectifier {i+1} Faulty Modules'] = rectifier.get('faulty_modules') if rectifier else None
                export_row[f'Rectifier {i+1} Space for New Modules'] = rectifier.get('space_for_new_modules') if rectifier else None
                export_row[f'Rectifier {i+1} Grounding'] = rectifier.get('grounding_of_rectifier') if rectifier else None
                export_row[f'Rectifier {i+1} SPD'] = rectifier.get('spd_in_rectifier') if rectifier else None
                export_row[f'Rectifier {i+1} SPD Model'] = rectifier.get('spd_model') if rectifier else None
                export_row[f'Rectifier {i+1} Total Installed SPDs'] = rectifier.get('total_installed_spds') if rectifier else None
                export_row[f'Rectifier {i+1} No of Faulty SPDs'] = rectifier.get('no_of_faulty_spds') if rectifier else None

            # Flatten DGs
            for i in range(max_dgs):
                dg = row['DGs'][i] if i < len(row['DGs']) else {}
                export_row[f'DG {i+1} Installed DG'] = dg.get('Installed DG')
                export_row[f'DG {i+1} Engine Make'] = dg.get('Engine Make')
                export_row[f'DG {i+1} Installation Year'] = dg.get('Installation Year')
                export_row[f'DG {i+1} DG Status'] = dg.get('DG Status')
                export_row[f'DG {i+1} DG Starting Battery'] = dg.get('DG Starting Battery')
                export_row[f'DG {i+1} Smart Switch Installed'] = dg.get('Smart Switch Installed')
                export_row[f'DG {i+1} ATS Installed'] = dg.get('ATS Installed')
                export_row[f'DG {i+1} ATS Capacity'] = dg.get('ATS Capacity')
                export_row[f'DG {i+1} Name of Faulty ATS Parts'] = dg.get('Name of Faulty ATS Parts')
                export_row[f'DG {i+1} No of Faulty ATS Parts'] = dg.get('No of Faulty ATS Parts')
                export_row[f'DG {i+1} Load on DG P1'] = dg.get('Load on DG P1')
                export_row[f'DG {i+1} Load on DG P2'] = dg.get('Load on DG P2')
                export_row[f'DG {i+1} Load on DG P3'] = dg.get('Load on DG P3')
                export_row[f'DG {i+1} Site Load Total'] = dg.get('Site Load Total')
                export_row[f'DG {i+1} Site Load P1'] = dg.get('Site Load P1')
                export_row[f'DG {i+1} Site Load P2'] = dg.get('Site Load P2')
                export_row[f'DG {i+1} Site Load P3'] = dg.get('Site Load P3')

            # Flatten Battery Banks
            for i in range(max_battery_banks):
                bb = row['Battery Banks'][i] if i < len(row['Battery Banks']) else {}
                export_row[f'Battery {i+1} Make'] = bb.get('Make of Battery')
                export_row[f'Battery {i+1} Capacity'] = bb.get('Battery Capacity')
                export_row[f'Battery {i+1} Type'] = bb.get('Battery Type')
                export_row[f'Battery {i+1} No of Cells/Bank'] = bb.get('No of Cells/Bank')
                export_row[f'Battery {i+1} Date of Installation'] = bb.get('Date of Installation')
                export_row[f'Battery {i+1} Load on Battery Bank'] = bb.get('Load on Battery Bank')
                export_row[f'Battery {i+1} Practical Backup Time'] = bb.get('Practical Backup Time')
                export_row[f'Battery {i+1} Installed (New/Used)'] = bb.get('Battery Installed (New/Used)')
                export_row[f'Battery {i+1} Moved From'] = bb.get('Battery Moved From')

            # Flatten AC Units
            for i in range(max_ac_units):
                ac = row['AC Units'][i] if i < len(row['AC Units']) else {}
                export_row[f'AC {i+1} Location'] = ac.get('Location')
                export_row[f'AC {i+1} Working Status'] = ac.get('Working Status')
                export_row[f'AC {i+1} Make'] = ac.get('AC Make')
                export_row[f'AC {i+1} Capacity (Tons)'] = ac.get('Capacity (Tons)')
                export_row[f'AC {i+1} Type'] = ac.get('Type of AC')
                export_row[f'AC {i+1} Mount Type'] = ac.get('Mount Type')
                export_row[f'AC {i+1} Date of Installation'] = ac.get('Date of Installation')
                export_row[f'AC {i+1} Sequence Controller Installed'] = ac.get('Sequence Controller Installed')
                export_row[f'AC {i+1} AC Load'] = ac.get('AC Load')
                export_row[f'AC {i+1} Total AC Load'] = ac.get('Total AC Load')
                export_row[f'AC {i+1} Fault Nature'] = ac.get('Fault Nature of AC Unit')
                export_row[f'AC {i+1} Estimate to Repair'] = ac.get('Estimate to Repair AC')

            # Flatten Solar Info
            export_row['Total Solar Size'] = row['Solar Info'].get('Total Solar Size')
            export_row['PV Solar Panel Capacity'] = row['Solar Info'].get('PV Solar Panel Capacity')
            export_row['No of PV Panels Installed'] = row['Solar Info'].get('No of PV Panels Installed')
            export_row['Make of PV Panels'] = row['Solar Info'].get('Make of PV Panels')
            export_row['Charge Controller Make'] = row['Solar Info'].get('Charge Controller Make')

            # Flatten Colocation Info
            export_row['Colocation'] = row['Colocation Info'].get('Colocation')
            export_row['Name of Colocation Vendors'] = row['Colocation Info'].get('Name of Colocation Vendors')
            export_row['Load of Each Vendor'] = row['Colocation Info'].get('Load of Each Vendor')
            export_row['Total Load'] = row['Colocation Info'].get('Total Load')

            # Flatten Building Info
            export_row['Building Status'] = row['Building Info'].get('Building Status')
            export_row['Wall/Doors Condition'] = row['Building Info'].get('Wall/Doors Condition')

            # Flatten Alarms
            for i in range(max_alarms):
                alarm = row['Alarms'][i] if i < len(row['Alarms']) else {}
                export_row[f'Alarm {i+1} AC Main Failure'] = alarm.get('AC Main Failure')
                export_row[f'Alarm {i+1} DC Low Voltages'] = alarm.get('DC Low Voltages')
                export_row[f'Alarm {i+1} Rectifier Failure'] = alarm.get('Rectifier Failure')

            # Flatten Earthings
            for i in range(max_earthings):
                earthing = row['Earthings'][i] if i < len(row['Earthings']) else {}
                export_row[f'Earthing {i+1} Value'] = earthing.get('Earthing Value')
                export_row[f'Earthing {i+1} No of Pits'] = earthing.get('No of Pits')

            # Flatten Fire Extinguishers
            for i in range(max_fire_extinguishers):
                fe = row['Fire Extinguishers'][i] if i < len(row['Fire Extinguishers']) else {}
                export_row[f'FE {i+1} Installed'] = fe.get('Installed')
                export_row[f'FE {i+1} No of FEs'] = fe.get('No of FEs')
                export_row[f'FE {i+1} Type of Gas'] = fe.get('Type of Gas')
                export_row[f'FE {i+1} Date of Expiry'] = fe.get('Date of Expiry')

            # Flatten PMR Infos
            for i in range(max_pmr_infos):
                pmr = row['PMR Infos'][i] if i < len(row['PMR Infos']) else {}
                export_row[f'PMR {i+1} Performed'] = pmr.get('PMR Performed')
                export_row[f'PMR {i+1} Last Performed Date'] = pmr.get('Last Performed Date')

            export_data.append(export_row)

        # Define section groups for labeling dynamically
        section_groups = {
            'Site Data': ['SN', 'Region', 'Domain', 'Site Name', 'Site LIC', 'FLC', 'Site Category', 'NEs Installed', 'Latitude', 'Longitude', 'Tower Available'] + [f'Tower {i+1} Type/Height' for i in range(max_towers)],
            'Power Information': ['WAPDA Ref Number', 'Transformer Capacity', 'Transformer Earthing', 'Working Status (Power)', 'Name of NEs Connected', 'Load of Individual NE'] + 
                             [f'Rectifier {i+1} Make' for i in range(max_rectifiers)] + 
                             [f'Rectifier {i+1} Capacity' for i in range(max_rectifiers)] + 
                             [f'Rectifier {i+1} No of Modules' for i in range(max_rectifiers)] + 
                             [f'Rectifier {i+1} Capacity of Each Module' for i in range(max_rectifiers)] + 
                             [f'Rectifier {i+1} Working Modules' for i in range(max_rectifiers)] + 
                             [f'Rectifier {i+1} Faulty Modules' for i in range(max_rectifiers)] + 
                             [f'Rectifier {i+1} Space for New Modules' for i in range(max_rectifiers)] + 
                             [f'Rectifier {i+1} Grounding' for i in range(max_rectifiers)] + 
                             [f'Rectifier {i+1} SPD' for i in range(max_rectifiers)] + 
                             [f'Rectifier {i+1} SPD Model' for i in range(max_rectifiers)] + 
                             [f'Rectifier {i+1} Total Installed SPDs' for i in range(max_rectifiers)] + 
                             [f'Rectifier {i+1} No of Faulty SPDs' for i in range(max_rectifiers)],
            'DG Information': [f'DG {i+1} Installed DG' for i in range(max_dgs)] + 
                             [f'DG {i+1} Engine Make' for i in range(max_dgs)] + 
                             [f'DG {i+1} Installation Year' for i in range(max_dgs)] + 
                             [f'DG {i+1} DG Status' for i in range(max_dgs)] + 
                             [f'DG {i+1} DG Starting Battery' for i in range(max_dgs)] + 
                             [f'DG {i+1} Smart Switch Installed' for i in range(max_dgs)] + 
                             [f'DG {i+1} ATS Installed' for i in range(max_dgs)] + 
                             [f'DG {i+1} ATS Capacity' for i in range(max_dgs)] + 
                             [f'DG {i+1} Name of Faulty ATS Parts' for i in range(max_dgs)] + 
                             [f'DG {i+1} No of Faulty ATS Parts' for i in range(max_dgs)] + 
                             [f'DG {i+1} Load on DG P1' for i in range(max_dgs)] + 
                             [f'DG {i+1} Load on DG P2' for i in range(max_dgs)] + 
                             [f'DG {i+1} Load on DG P3' for i in range(max_dgs)] + 
                             [f'DG {i+1} Site Load Total' for i in range(max_dgs)] + 
                             [f'DG {i+1} Site Load P1' for i in range(max_dgs)] + 
                             [f'DG {i+1} Site Load P2' for i in range(max_dgs)] + 
                             [f'DG {i+1} Site Load P3' for i in range(max_dgs)],
            'Battery Bank Information': [f'Battery {i+1} Make' for i in range(max_battery_banks)] + 
                                       [f'Battery {i+1} Capacity' for i in range(max_battery_banks)] + 
                                       [f'Battery {i+1} Type' for i in range(max_battery_banks)] + 
                                       [f'Battery {i+1} No of Cells/Bank' for i in range(max_battery_banks)] + 
                                       [f'Battery {i+1} Date of Installation' for i in range(max_battery_banks)] + 
                                       [f'Battery {i+1} Load on Battery Bank' for i in range(max_battery_banks)] + 
                                       [f'Battery {i+1} Practical Backup Time' for i in range(max_battery_banks)] + 
                                       [f'Battery {i+1} Installed (New/Used)' for i in range(max_battery_banks)] + 
                                       [f'Battery {i+1} Moved From' for i in range(max_battery_banks)],
            'AC Units Information': [f'AC {i+1} Location' for i in range(max_ac_units)] + 
                                   [f'AC {i+1} Working Status' for i in range(max_ac_units)] + 
                                   [f'AC {i+1} Make' for i in range(max_ac_units)] + 
                                   [f'AC {i+1} Capacity (Tons)' for i in range(max_ac_units)] + 
                                   [f'AC {i+1} Type' for i in range(max_ac_units)] + 
                                   [f'AC {i+1} Mount Type' for i in range(max_ac_units)] + 
                                   [f'AC {i+1} Date of Installation' for i in range(max_ac_units)] + 
                                   [f'AC {i+1} Sequence Controller Installed' for i in range(max_ac_units)] + 
                                   [f'AC {i+1} AC Load' for i in range(max_ac_units)] + 
                                   [f'AC {i+1} Total AC Load' for i in range(max_ac_units)] + 
                                   [f'AC {i+1} Fault Nature' for i in range(max_ac_units)] + 
                                   [f'AC {i+1} Estimate to Repair' for i in range(max_ac_units)],
            'Solar Information': ['Total Solar Size', 'PV Solar Panel Capacity', 'No of PV Panels Installed', 'Make of PV Panels', 'Charge Controller Make'],
            'Colocation Information': ['Colocation', 'Name of Colocation Vendors', 'Load of Each Vendor', 'Total Load'],
            'Building Information': ['Building Status', 'Wall/Doors Condition'],
            'Alarms': [f'Alarm {i+1} AC Main Failure' for i in range(max_alarms)] + 
                     [f'Alarm {i+1} DC Low Voltages' for i in range(max_alarms)] + 
                     [f'Alarm {i+1} Rectifier Failure' for i in range(max_alarms)],
            'Earthings': [f'Earthing {i+1} Value' for i in range(max_earthings)] + 
                        [f'Earthing {i+1} No of Pits' for i in range(max_earthings)],
            'Fire Extinguishers': [f'FE {i+1} Installed' for i in range(max_fire_extinguishers)] + 
                                 [f'FE {i+1} No of FEs' for i in range(max_fire_extinguishers)] + 
                                 [f'FE {i+1} Type of Gas' for i in range(max_fire_extinguishers)] + 
                                 [f'FE {i+1} Date of Expiry' for i in range(max_fire_extinguishers)],
            'PMR Information': [f'PMR {i+1} Performed' for i in range(max_pmr_infos)] + 
                              [f'PMR {i+1} Last Performed Date' for i in range(max_pmr_infos)]
        }

        # Create DataFrame with flattened data
        df = pd.DataFrame(export_data)

        # Reorder columns according to section groups
        ordered_columns = []
        for section, cols in section_groups.items():
            ordered_columns.extend(cols)
        df = df[ordered_columns]

        # Create a list for section labels (to be inserted as a row)
        section_labels = [''] * len(df.columns)
        col_idx = 0
        for section, cols in section_groups.items():
            if cols:
                section_labels[col_idx] = section
                col_idx += len(cols)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Write section labels as the first row
            pd.DataFrame([section_labels], columns=df.columns).to_excel(writer, sheet_name='Filtered_Exchanges', index=False, startrow=0)
            # Write the actual data starting from the second row
            df.to_excel(writer, sheet_name='Filtered_Exchanges', index=False, startrow=1)

            worksheet = writer.sheets['Filtered_Exchanges']
            # Auto-adjust column widths
            for idx, col in enumerate(df.columns):
                max_len = max(
                    df[col].astype(str).map(len).max() if not df[col].empty else 0,
                    len(col),
                    len(section_labels[idx] or '')
                ) + 2
                worksheet.set_column(idx, idx, max_len)

            # Optionally, apply formatting to section labels (e.g., bold)
            workbook = writer.book
            bold_format = workbook.add_format({'bold': True})
            for col_idx, label in enumerate(section_labels):
                if label:
                    worksheet.write(0, col_idx, label, bold_format)

        output.seek(0)
        return send_file(
            output,
            download_name='filtered_exchanges.xlsx',
            as_attachment=True,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    return render_template('filters.html', table_data=table_data, available_domains=available_domains, available_categories=available_categories, selected_domain=domain_filter, selected_category=category_filter, max_rectifiers=max_rectifiers)

    
if __name__ == '__main__':
    app.run(debug=True)