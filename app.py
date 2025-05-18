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
    transformer_earthing = db.Column(db.String(50))
    working_status = db.Column(db.Boolean)
    load_of_individual_ne = db.Column(db.Float, nullable=True)
    name_of_nes_connected = db.Column(db.Text)
    make_of_rectifier = db.Column(db.String(50), nullable=True)
    rectifier_capacity = db.Column(db.Float, nullable=True)
    no_of_modules = db.Column(db.Integer, nullable=True)
    capacity_of_each_module = db.Column(db.Float, nullable=True)
    working_modules = db.Column(db.Integer, nullable=True)
    faulty_modules = db.Column(db.Integer, nullable=True)
    space_for_new_modules = db.Column(db.Integer, nullable=True)
    grounding_of_rectifier = db.Column(db.Boolean, nullable=True)
    spd_in_rectifier = db.Column(db.Boolean, nullable=True)
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
    dg_status = db.Column(db.String(50))
    dg_starting_battery = db.Column(db.String(50))
    smart_switch_installed = db.Column(db.Boolean, nullable=True)
    ats_installed = db.Column(db.Boolean, nullable=True)
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
    battery_type = db.Column(db.String(50))
    no_of_cells_bank = db.Column(db.Integer, nullable=True)
    date_of_installation = db.Column(db.String(50))
    load_on_battery_bank = db.Column(db.Float, nullable=True)
    practical_backup_time = db.Column(db.Float, nullable=True)
    battery_installed_new_or_used = db.Column(db.String(50))
    battery_moved_from = db.Column(db.String(100))

class ACUnit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn', ondelete='CASCADE'))
    location_of_ac_unit = db.Column(db.String(100))
    working_status = db.Column(db.Boolean, nullable=True)
    ac_make = db.Column(db.String(50))
    capacity_tons = db.Column(db.Float, nullable=True)
    type_of_ac = db.Column(db.String(50))
    mount_type = db.Column(db.String(50))
    date_of_installation = db.Column(db.String(50))
    sequence_controller_installed = db.Column(db.Boolean, nullable=True)
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
    colocation = db.Column(db.Boolean, default=False, nullable=True)
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
    ac_main_failure = db.Column(db.Boolean, nullable=True)
    dc_low_voltages = db.Column(db.Boolean, nullable=True)
    rectifier_failure = db.Column(db.Boolean, nullable=True)

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
    fe_installed = db.Column(db.Boolean, nullable=True)
    no_of_fes = db.Column(db.Integer, nullable=True)
    type_of_gas = db.Column(db.String(50), nullable=True)
    date_of_expiry = db.Column(db.String(50), nullable=True)

class PMRInformation(db.Model):
    __tablename__ = 'pmr_information'
    id = db.Column(db.Integer, primary_key=True)
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn', ondelete='CASCADE'))
    pmr_performed = db.Column(db.Boolean, nullable=True)
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
            exchanges = GeneralInformation.query.filter_by(domain=user_region).all()

        regions = db.session.query(GeneralInformation.domain, db.func.count(GeneralInformation.sn)).group_by(GeneralInformation.domain).all()
        region_labels = [r[0] for r in regions if r[0] is not None]
        region_counts = [r[1] for r in regions if r[0] is not None]

        total_exchanges = len(exchanges)
        year_counts = [total_exchanges // 2, total_exchanges - (total_exchanges // 2)]
        year_labels = ['2024', '2025']

        total_exchanges = len(exchanges)
        operational_exchanges = sum(1 for e in exchanges if e.power_info and e.power_info.working_status)
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
        flash(f"Error: {str(e)}")
        return redirect(url_for('index'))

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        try:
            last_sn = db.session.query(db.func.max(GeneralInformation.sn)).scalar() or 0
            sn = last_sn + 1

            user_region = session.get('region')
            domain = request.form['domain'] if user_region == 'All' else user_region

            general = GeneralInformation(
                sn=sn,
                region='RTR',
                domain=domain,
                exchange_name=request.form['exchange_name'],
                exchange_lic=request.form['exchange_lic'],
                flc=request.form['flc'],
                site_category=request.form['site_category'],
                nes_installed=request.form['nes_installed'],
                latitude=float(request.form['latitude']) if request.form['latitude'].strip() else None,
                longitude=float(request.form['longitude']) if request.form['longitude'].strip() else None,
                tower_available=request.form['tower_available']
            )

            if general.tower_available == 'Yes':
                tower_types = request.form.getlist('tower_type_height[]')
                for tower_type in tower_types:
                    if tower_type:
                        tower = Tower(tower_type_height=tower_type)
                        general.towers.append(tower)

            power_info = PowerInformation(
                wapda_ref_number=request.form['wapda_ref_number'],
                transformer_capacity=request.form['transformer_capacity'],
                transformer_earthing=request.form['transformer_earthing'],
                working_status='working_status_power' in request.form,
                load_of_individual_ne=float(request.form['load_of_individual_ne']) if request.form['load_of_individual_ne'].strip() else None,
                name_of_nes_connected=request.form['name_of_nes_connected'],
                make_of_rectifier=request.form.getlist('make_of_rectifier[]')[0] if request.form.getlist('make_of_rectifier[]') and request.form.getlist('make_of_rectifier[]')[0].strip() else None,
                rectifier_capacity=float(request.form.getlist('rectifier_capacity[]')[0]) if request.form.getlist('rectifier_capacity[]') and request.form.getlist('rectifier_capacity[]')[0].strip() else None,
                no_of_modules=int(request.form.getlist('no_of_modules[]')[0]) if request.form.getlist('no_of_modules[]') and request.form.getlist('no_of_modules[]')[0].strip() else None,
                capacity_of_each_module=float(request.form.getlist('capacity_of_each_module[]')[0]) if request.form.getlist('capacity_of_each_module[]') and request.form.getlist('capacity_of_each_module[]')[0].strip() else None,
                working_modules=int(request.form.getlist('working_modules[]')[0]) if request.form.getlist('working_modules[]') and request.form.getlist('working_modules[]')[0].strip() else None,
                faulty_modules=int(request.form.getlist('faulty_modules[]')[0]) if request.form.getlist('faulty_modules[]') and request.form.getlist('faulty_modules[]')[0].strip() else None,
                space_for_new_modules=int(request.form.getlist('space_for_new_modules[]')[0]) if request.form.getlist('space_for_new_modules[]') and request.form.getlist('space_for_new_modules[]')[0].strip() else None,
                grounding_of_rectifier='grounding_of_rectifier[]' in request.form and request.form.getlist('grounding_of_rectifier[]')[0] == 'on',
                spd_in_rectifier='spd_in_rectifier[]' in request.form and request.form.getlist('spd_in_rectifier[]')[0] == 'on',
                spd_model=request.form.getlist('spd_model[]')[0] if request.form.getlist('spd_model[]') and request.form.getlist('spd_model[]')[0].strip() else None,
                total_installed_spds=int(request.form.getlist('total_installed_spds[]')[0]) if request.form.getlist('total_installed_spds[]') and request.form.getlist('total_installed_spds[]')[0].strip() else None,
                no_of_faulty_spds=int(request.form.getlist('no_of_faulty_spds[]')[0]) if request.form.getlist('no_of_faulty_spds[]') and request.form.getlist('no_of_faulty_spds[]')[0].strip() else None
            )
            general.power_info = power_info

            installed_dgs = request.form.getlist('installed_dg[]')
            for i in range(len(installed_dgs)):
                if installed_dgs[i]:
                    dg = DGInformation(
                        installed_dg=installed_dgs[i],
                        engine_make=request.form.getlist('engine_make[]')[i],
                        installation_year=int(request.form.getlist('installation_year[]')[i]) if request.form.getlist('installation_year[]')[i].strip() else None,
                        dg_status=request.form.getlist('dg_status[]')[i],
                        dg_starting_battery=request.form.getlist('dg_starting_battery[]')[i],
                        smart_switch_installed='smart_switch_installed[]' in request.form and request.form.getlist('smart_switch_installed[]')[i] == 'on',
                        ats_installed='ats_installed[]' in request.form and request.form.getlist('ats_installed[]')[i] == 'on',
                        ats_capacity=request.form.getlist('ats_capacity[]')[i] or None,
                        name_of_faulty_ats_parts=request.form.getlist('name_of_faulty_ats_parts[]')[i] or None,
                        no_of_faulty_ats_parts=int(request.form.getlist('no_of_faulty_ats_parts[]')[i]) if request.form.getlist('no_of_faulty_ats_parts[]')[i].strip() else None,
                        load_on_dg_p1=float(request.form.getlist('load_on_dg_p1[]')[i]) if request.form.getlist('load_on_dg_p1[]')[i].strip() else None,
                        load_on_dg_p2=float(request.form.getlist('load_on_dg_p2[]')[i]) if request.form.getlist('load_on_dg_p2[]')[i].strip() else None,
                        load_on_dg_p3=float(request.form.getlist('load_on_dg_p3[]')[i]) if request.form.getlist('load_on_dg_p3[]')[i].strip() else None,
                        site_load_total=float(request.form.getlist('site_load_total[]')[i]) if request.form.getlist('site_load_total[]')[i].strip() else None,
                        site_load_p1=float(request.form.getlist('site_load_p1[]')[i]) if request.form.getlist('site_load_p1[]')[i].strip() else None,
                        site_load_p2=float(request.form.getlist('site_load_p2[]')[i]) if request.form.getlist('site_load_p2[]')[i].strip() else None,
                        site_load_p3=float(request.form.getlist('site_load_p3[]')[i]) if request.form.getlist('site_load_p3[]')[i].strip() else None
                    )
                    general.dgs.append(dg)

            makes_of_battery = request.form.getlist('make_of_battery[]')
            for i in range(len(makes_of_battery)):
                if makes_of_battery[i]:
                    battery = BatteryBank(
                        make_of_battery=makes_of_battery[i],
                        battery_capacity=float(request.form.getlist('battery_capacity[]')[i]) if request.form.getlist('battery_capacity[]')[i].strip() else None,
                        battery_type=request.form.getlist('battery_type[]')[i],
                        no_of_cells_bank=int(request.form.getlist('no_of_cells_bank[]')[i]) if request.form.getlist('no_of_cells_bank[]')[i].strip() else None,
                        date_of_installation=request.form.getlist('date_of_installation_battery[]')[i] or None,
                        load_on_battery_bank=float(request.form.getlist('load_on_battery_bank[]')[i]) if request.form.getlist('load_on_battery_bank[]')[i].strip() else None,
                        practical_backup_time=float(request.form.getlist('practical_backup_time[]')[i]) if request.form.getlist('practical_backup_time[]')[i].strip() else None,
                        battery_installed_new_or_used=request.form.getlist('battery_installed_new_or_used[]')[i] or None,
                        battery_moved_from=request.form.getlist('battery_moved_from[]')[i] or None
                    )
                    general.battery_banks.append(battery)

            locations = request.form.getlist('location_of_ac_unit[]')
            for i in range(len(locations)):
                if locations[i]:
                    ac = ACUnit(
                        location_of_ac_unit=locations[i],
                        working_status='working_status_ac[]' in request.form and request.form.getlist('working_status_ac[]')[i] == 'on',
                        ac_make=request.form.getlist('ac_make[]')[i] or None,
                        capacity_tons=float(request.form.getlist('capacity_tons[]')[i]) if request.form.getlist('capacity_tons[]')[i].strip() else None,
                        type_of_ac=request.form.getlist('type_of_ac[]')[i] or None,
                        mount_type=request.form.getlist('mount_type[]')[i] or None,
                        date_of_installation=request.form.getlist('date_of_installation_ac[]')[i] or None,
                        sequence_controller_installed='sequence_controller_installed[]' in request.form and request.form.getlist('sequence_controller_installed[]')[i] == 'on',
                        ac_load=float(request.form.getlist('ac_load[]')[i]) if request.form.getlist('ac_load[]')[i].strip() else None,
                        total_ac_load=float(request.form.getlist('total_ac_load[]')[i]) if request.form.getlist('total_ac_load[]')[i].strip() else None,
                        fault_nature_of_ac_unit=request.form.getlist('fault_nature_of_ac_unit[]')[i] or None,
                        estimate_to_repair_ac=float(request.form.getlist('estimate_to_repair_ac[]')[i]) if request.form.getlist('estimate_to_repair_ac[]')[i].strip() else None
                    )
                    general.ac_units.append(ac)

            solar_info = SolarInformation(
                total_solar_size=float(request.form['total_solar_size']) if request.form['total_solar_size'].strip() else None,
                pv_solar_panel_capacity=float(request.form['pv_solar_panel_capacity']) if request.form['pv_solar_panel_capacity'].strip() else None,
                no_of_pv_panels_installed=int(request.form['no_of_pv_panels_installed']) if request.form['no_of_pv_panels_installed'].strip() else None,
                make_of_pv_panels=request.form['make_of_pv_panels'] or None,
                charge_controller_make=request.form['charge_controller_make'] or None
            )
            general.solar_info = solar_info

            colocation_info = ColocationInformation(
                colocation='colocation' in request.form,
                name_of_colocation_vendors=request.form['name_of_colocation_vendors'] or None,
                load_of_each_vendor=float(request.form['load_of_each_vendor']) if request.form['load_of_each_vendor'].strip() else None,
                total_load=float(request.form['total_load']) if request.form['total_load'].strip() else None
            )
            general.colocation_info = colocation_info

            building_info = BuildingInformation(
                building_status=request.form['building_status'],
                wall_doors_condition=request.form['wall_doors_condition']
            )
            general.building_info = building_info

            # Alarm Extension
            alarms = []
            ac_main_failures = request.form.getlist('ac_main_failure[]')
            for i in range(len(ac_main_failures)):
                alarm = AlarmExtension(
                    ac_main_failure=ac_main_failures[i] == 'on',
                    dc_low_voltages=request.form.getlist('dc_low_voltages[]')[i] == 'on',
                    rectifier_failure=request.form.getlist('rectifier_failure[]')[i] == 'on'
                )
                alarms.append(alarm)
            general.alarms = alarms

            # Earthing
            earthings = []
            earthing_values = request.form.getlist('earthing_value[]')
            for i in range(len(earthing_values)):
                if earthing_values[i]:
                    earthing = Earthing(
                        earthing_value=float(earthing_values[i]) if earthing_values[i].strip() else None,
                        no_of_pits=int(request.form.getlist('no_of_pits[]')[i]) if request.form.getlist('no_of_pits[]')[i].strip() else None
                    )
                    earthings.append(earthing)
            general.earthings = earthings

            # Fire Extinguisher
            fire_extinguishers = []
            fe_installeds = request.form.getlist('fe_installed[]')
            for i in range(len(fe_installeds)):
                fire_ext = FireExtinguisher(
                    fe_installed=fe_installeds[i] == 'on',
                    no_of_fes=int(request.form.getlist('no_of_fes[]')[i]) if request.form.getlist('no_of_fes[]')[i].strip() else None,
                    type_of_gas=request.form.getlist('type_of_gas[]')[i] or None,
                    date_of_expiry=request.form.getlist('date_of_expiry[]')[i] or None
                )
                fire_extinguishers.append(fire_ext)
            general.fire_extinguishers = fire_extinguishers

            # PMR Information
            pmr_infos = []
            pmr_performeds = request.form.getlist('pmr_performed[]')
            for i in range(len(pmr_performeds)):
                pmr = PMRInformation(
                    pmr_performed=pmr_performeds[i] == 'on',
                    last_performed_date=request.form.getlist('last_performed_date[]')[i] or None
                )
                pmr_infos.append(pmr)
            general.pmr_infos = pmr_infos

            db.session.add(general)
            db.session.commit()
            flash('Exchange added successfully!')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
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
            # Use no_autoflush to prevent premature flushing
            with db.session.no_autoflush:
                general.region = 'RTR'
                general.domain = request.form['domain'] if user_region == 'All' else user_region
                general.exchange_name = request.form['exchange_name']
                general.exchange_lic = request.form['exchange_lic']
                general.flc = request.form['flc']
                general.site_category = request.form['site_category']
                general.nes_installed = request.form['nes_installed']
                general.latitude = float(request.form['latitude']) if request.form['latitude'].strip() else None
                general.longitude = float(request.form['longitude']) if request.form['longitude'].strip() else None
                general.tower_available = request.form['tower_available']

                if general.tower_available == 'Yes':
                    general.towers = []
                    tower_types = request.form.getlist('tower_type_height[]')
                    for tower_type in tower_types:
                        if tower_type:
                            tower = Tower(tower_type_height=tower_type)
                            general.towers.append(tower)
                else:
                    general.towers = []

                if not general.power_info:
                    general.power_info = PowerInformation()
                general.power_info.wapda_ref_number = request.form['wapda_ref_number']
                general.power_info.transformer_capacity = request.form['transformer_capacity']
                general.power_info.transformer_earthing = request.form['transformer_earthing']
                general.power_info.working_status = 'working_status_power' in request.form
                general.power_info.load_of_individual_ne = float(request.form['load_of_individual_ne']) if request.form['load_of_individual_ne'].strip() else None
                general.power_info.name_of_nes_connected = request.form['name_of_nes_connected']
                make_of_rectifiers = request.form.getlist('make_of_rectifier[]')
                general.power_info.make_of_rectifier = make_of_rectifiers[0] if make_of_rectifiers and make_of_rectifiers[0].strip() else None

                rectifier_capacities = request.form.getlist('rectifier_capacity[]')
                general.power_info.rectifier_capacity = float(rectifier_capacities[0]) if rectifier_capacities and rectifier_capacities[0].strip() else None

                no_of_modules_list = request.form.getlist('no_of_modules[]')
                general.power_info.no_of_modules = int(no_of_modules_list[0]) if no_of_modules_list and no_of_modules_list[0].strip() else None

                capacity_of_each_module_list = request.form.getlist('capacity_of_each_module[]')
                general.power_info.capacity_of_each_module = float(capacity_of_each_module_list[0]) if capacity_of_each_module_list and capacity_of_each_module_list[0].strip() else None

                working_modules_list = request.form.getlist('working_modules[]')
                general.power_info.working_modules = int(working_modules_list[0]) if working_modules_list and working_modules_list[0].strip() else None

                faulty_modules_list = request.form.getlist('faulty_modules[]')
                general.power_info.faulty_modules = int(faulty_modules_list[0]) if faulty_modules_list and faulty_modules_list[0].strip() else None

                space_for_new_modules_list = request.form.getlist('space_for_new_modules[]')
                general.power_info.space_for_new_modules = int(space_for_new_modules_list[0]) if space_for_new_modules_list and space_for_new_modules_list[0].strip() else None

                # Fix grounding_of_rectifier handling
                general.power_info.grounding_of_rectifier = 'grounding_of_rectifier[]' in request.form and request.form.getlist('grounding_of_rectifier[]')[0] == 'on'

                # Fix spd_in_rectifier handling
                general.power_info.spd_in_rectifier = 'spd_in_rectifier[]' in request.form and request.form.getlist('spd_in_rectifier[]')[0] == 'on'

                spd_models = request.form.getlist('spd_model[]')
                general.power_info.spd_model = spd_models[0] if spd_models and spd_models[0].strip() else None

                total_installed_spds_list = request.form.getlist('total_installed_spds[]')
                general.power_info.total_installed_spds = int(total_installed_spds_list[0]) if total_installed_spds_list and total_installed_spds_list[0].strip() else None

                no_of_faulty_spds_list = request.form.getlist('no_of_faulty_spds[]')
                general.power_info.no_of_faulty_spds = int(no_of_faulty_spds_list[0]) if no_of_faulty_spds_list and no_of_faulty_spds_list[0].strip() else None

                general.dgs = []
                installed_dgs = request.form.getlist('installed_dg[]')
                for i in range(len(installed_dgs)):
                    if installed_dgs[i]:
                        dg = DGInformation(
                            installed_dg=installed_dgs[i],
                            engine_make=request.form.getlist('engine_make[]')[i],
                            installation_year=int(request.form.getlist('installation_year[]')[i]) if request.form.getlist('installation_year[]')[i].strip() else None,
                            dg_status=request.form.getlist('dg_status[]')[i],
                            dg_starting_battery=request.form.getlist('dg_starting_battery[]')[i],
                            smart_switch_installed='smart_switch_installed[]' in request.form and request.form.getlist('smart_switch_installed[]')[i] == 'on',
                            ats_installed='ats_installed[]' in request.form and request.form.getlist('ats_installed[]')[i] == 'on',
                            ats_capacity=request.form.getlist('ats_capacity[]')[i] or None,
                            name_of_faulty_ats_parts=request.form.getlist('name_of_faulty_ats_parts[]')[i] or None,
                            no_of_faulty_ats_parts=int(request.form.getlist('no_of_faulty_ats_parts[]')[i]) if request.form.getlist('no_of_faulty_ats_parts[]')[i].strip() else None,
                            load_on_dg_p1=float(request.form.getlist('load_on_dg_p1[]')[i]) if request.form.getlist('load_on_dg_p1[]')[i].strip() else None,
                            load_on_dg_p2=float(request.form.getlist('load_on_dg_p2[]')[i]) if request.form.getlist('load_on_dg_p2[]')[i].strip() else None,
                            load_on_dg_p3=float(request.form.getlist('load_on_dg_p3[]')[i]) if request.form.getlist('load_on_dg_p3[]')[i].strip() else None,
                            site_load_total=float(request.form.getlist('site_load_total[]')[i]) if request.form.getlist('site_load_total[]')[i].strip() else None,
                            site_load_p1=float(request.form.getlist('site_load_p1[]')[i]) if request.form.getlist('site_load_p1[]')[i].strip() else None,
                            site_load_p2=float(request.form.getlist('site_load_p2[]')[i]) if request.form.getlist('site_load_p2[]')[i].strip() else None,
                            site_load_p3=float(request.form.getlist('site_load_p3[]')[i]) if request.form.getlist('site_load_p3[]')[i].strip() else None
                        )
                        general.dgs.append(dg)

                general.battery_banks = []
                makes_of_battery = request.form.getlist('make_of_battery[]')
                for i in range(len(makes_of_battery)):
                    if makes_of_battery[i]:
                        battery = BatteryBank(
                            make_of_battery=makes_of_battery[i],
                            battery_capacity=float(request.form.getlist('battery_capacity[]')[i]) if request.form.getlist('battery_capacity[]')[i].strip() else None,
                            battery_type=request.form.getlist('battery_type[]')[i],
                            no_of_cells_bank=int(request.form.getlist('no_of_cells_bank[]')[i]) if request.form.getlist('no_of_cells_bank[]')[i].strip() else None,
                            date_of_installation=request.form.getlist('date_of_installation_battery[]')[i] or None,
                            load_on_battery_bank=float(request.form.getlist('load_on_battery_bank[]')[i]) if request.form.getlist('load_on_battery_bank[]')[i].strip() else None,
                            practical_backup_time=float(request.form.getlist('practical_backup_time[]')[i]) if request.form.getlist('practical_backup_time[]')[i].strip() else None,
                            battery_installed_new_or_used=request.form.getlist('battery_installed_new_or_used[]')[i] or None,
                            battery_moved_from=request.form.getlist('battery_moved_from[]')[i] or None
                        )
                        general.battery_banks.append(battery)

                general.ac_units = []
                locations = request.form.getlist('location_of_ac_unit[]')
                for i in range(len(locations)):
                    if locations[i]:
                        ac = ACUnit(
                            location_of_ac_unit=locations[i],
                            working_status='working_status_ac[]' in request.form and request.form.getlist('working_status_ac[]')[i] == 'on',
                            ac_make=request.form.getlist('ac_make[]')[i] or None,
                            capacity_tons=float(request.form.getlist('capacity_tons[]')[i]) if request.form.getlist('capacity_tons[]')[i].strip() else None,
                            type_of_ac=request.form.getlist('type_of_ac[]')[i] or None,
                            mount_type=request.form.getlist('mount_type[]')[i] or None,
                            date_of_installation=request.form.getlist('date_of_installation_ac[]')[i] or None,
                            sequence_controller_installed='sequence_controller_installed[]' in request.form and request.form.getlist('sequence_controller_installed[]')[i] == 'on',
                            ac_load=float(request.form.getlist('ac_load[]')[i]) if request.form.getlist('ac_load[]')[i].strip() else None,
                            total_ac_load=float(request.form.getlist('total_ac_load[]')[i]) if request.form.getlist('total_ac_load[]')[i].strip() else None,
                            fault_nature_of_ac_unit=request.form.getlist('fault_nature_of_ac_unit[]')[i] or None,
                            estimate_to_repair_ac=float(request.form.getlist('estimate_to_repair_ac[]')[i]) if request.form.getlist('estimate_to_repair_ac[]')[i].strip() else None
                        )
                        general.ac_units.append(ac)

                if not general.solar_info:
                    general.solar_info = SolarInformation()
                general.solar_info.total_solar_size = float(request.form['total_solar_size']) if request.form['total_solar_size'].strip() else None
                general.solar_info.pv_solar_panel_capacity = float(request.form['pv_solar_panel_capacity']) if request.form['pv_solar_panel_capacity'].strip() else None
                general.solar_info.no_of_pv_panels_installed = int(request.form['no_of_pv_panels_installed']) if request.form['no_of_pv_panels_installed'].strip() else None
                general.solar_info.make_of_pv_panels = request.form['make_of_pv_panels'] or None
                general.solar_info.charge_controller_make = request.form['charge_controller_make'] or None

                if not general.colocation_info:
                    general.colocation_info = ColocationInformation()
                general.colocation_info.colocation = 'colocation' in request.form
                general.colocation_info.name_of_colocation_vendors = request.form['name_of_colocation_vendors'] or None
                general.colocation_info.load_of_each_vendor = float(request.form['load_of_each_vendor']) if request.form['load_of_each_vendor'].strip() else None
                general.colocation_info.total_load = float(request.form['total_load']) if request.form['total_load'].strip() else None

                if not general.building_info:
                    general.building_info = BuildingInformation()
                general.building_info.building_status = request.form['building_status']
                general.building_info.wall_doors_condition = request.form['wall_doors_condition']

                # Update Alarm Extension
                general.alarms = []
                ac_main_failures = request.form.getlist('ac_main_failure[]')
                for i in range(len(ac_main_failures)):
                    alarm = AlarmExtension(
                        ac_main_failure=ac_main_failures[i] == 'on',
                        dc_low_voltages=request.form.getlist('dc_low_voltages[]')[i] == 'on',
                        rectifier_failure=request.form.getlist('rectifier_failure[]')[i] == 'on'
                    )
                    general.alarms.append(alarm)

                # Update Earthing
                general.earthings = []
                earthing_values = request.form.getlist('earthing_value[]')
                for i in range(len(earthing_values)):
                    if earthing_values[i]:
                        earthing = Earthing(
                            earthing_value=float(earthing_values[i]) if earthing_values[i].strip() else None,
                            no_of_pits=int(request.form.getlist('no_of_pits[]')[i]) if request.form.getlist('no_of_pits[]')[i].strip() else None
                        )
                        general.earthings.append(earthing)

                # Update Fire Extinguisher
                general.fire_extinguishers = []
                fe_installeds = request.form.getlist('fe_installed[]')
                for i in range(len(fe_installeds)):
                    fire_ext = FireExtinguisher(
                        fe_installed=fe_installeds[i] == 'on',
                        no_of_fes=int(request.form.getlist('no_of_fes[]')[i]) if request.form.getlist('no_of_fes[]')[i].strip() else None,
                        type_of_gas=request.form.getlist('type_of_gas[]')[i] or None,
                        date_of_expiry=request.form.getlist('date_of_expiry[]')[i] or None
                    )
                    general.fire_extinguishers.append(fire_ext)

                # Update PMR Information
                general.pmr_infos = []
                pmr_performeds = request.form.getlist('pmr_performed[]')
                for i in range(len(pmr_performeds)):
                    pmr = PMRInformation(
                        pmr_performed=pmr_performeds[i] == 'on',
                        last_performed_date=request.form.getlist('last_performed_date[]')[i] or None
                    )
                    general.pmr_infos.append(pmr)

            db.session.commit()
            flash('Exchange updated successfully!')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
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
        db.session.delete(general)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Exchange deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error deleting exchange: {str(e)}'}), 500

@app.route('/export')
@login_required
def export():
    try:
        user_region = session.get('region')
        if user_region == "All":
            exchanges = GeneralInformation.query.all()
        else:
            exchanges = GeneralInformation.query.filter_by(domain=user_region).all()

        if not exchanges:
            flash('No exchanges found to export.')
            return redirect(url_for('index'))

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
                'Exchange Name': exchange.exchange_name,
                'Exchange LIC': exchange.exchange_lic,
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
            # Optional: Adjust column widths for better readability
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
        return redirect(url_for('index'))
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
        exchanges = GeneralInformation.query.filter_by(domain=user_region).all()
    return render_template('view_exchanges.html', exchanges=exchanges)

if __name__ == '__main__':
    app.run(debug=True)