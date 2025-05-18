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
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    tower_available = db.Column(db.String(10))
    towers = db.relationship('Tower', backref='general_info', lazy=True, cascade="all, delete-orphan")
    power_info = db.relationship('PowerInformation', backref='general_info', uselist=False, cascade="all, delete-orphan")
    dgs = db.relationship('DGInformation', backref='general_info', lazy=True, cascade="all, delete-orphan")
    battery_banks = db.relationship('BatteryBank', backref='general_info', lazy=True, cascade="all, delete-orphan")
    ac_units = db.relationship('ACUnit', backref='general_info', lazy=True, cascade="all, delete-orphan")
    solar_info = db.relationship('SolarInformation', backref='general_info', uselist=False, cascade="all, delete-orphan")
    colocation_info = db.relationship('ColocationInformation', backref='general_info', uselist=False, cascade="all, delete-orphan")
    building_info = db.relationship('BuildingInformation', backref='general_info', uselist=False, cascade="all, delete-orphan")

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
    load_of_individual_ne = db.Column(db.Float)
    name_of_nes_connected = db.Column(db.Text)
    rectifiers = db.relationship('Rectifier', backref='power_info', lazy=True, cascade="all, delete-orphan")

class Rectifier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    power_id = db.Column(db.Integer, db.ForeignKey('power_information.id', ondelete='CASCADE'))
    make_of_rectifier = db.Column(db.String(50))
    rectifier_capacity = db.Column(db.Float)
    no_of_modules = db.Column(db.Integer)
    capacity_of_each_module = db.Column(db.Float)
    working_modules = db.Column(db.Integer)
    faulty_modules = db.Column(db.Integer)
    space_for_new_modules = db.Column(db.Integer)
    grounding_of_rectifier = db.Column(db.Boolean)
    spd_in_rectifier = db.Column(db.Boolean)
    spd_model = db.Column(db.String(50))
    total_installed_spds = db.Column(db.Integer)
    no_of_faulty_spds = db.Column(db.Integer)

class DGInformation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn', ondelete='CASCADE'))
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
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn', ondelete='CASCADE'))
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
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn', ondelete='CASCADE'))
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
    __tablename__ = 'installed_solar_information'
    id = db.Column(db.Integer, primary_key=True)
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn', ondelete='CASCADE'))
    total_solar_size = db.Column(db.Float)
    pv_solar_panel_capacity = db.Column(db.Float)
    no_of_pv_panels_installed = db.Column(db.Integer)
    make_of_pv_panels = db.Column(db.String(50))
    charge_controller_make = db.Column(db.String(50))

class ColocationInformation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn', ondelete='CASCADE'))
    colocation = db.Column(db.Boolean, default=False)
    name_of_colocation_vendors = db.Column(db.Text)
    load_of_each_vendor = db.Column(db.Float)
    total_load = db.Column(db.Float)

class BuildingInformation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn', ondelete='CASCADE'))
    building_type = db.Column(db.String(50))
    construction_year = db.Column(db.Integer)
    total_area_sqft = db.Column(db.Float)
    number_of_floors = db.Column(db.Integer)
    condition = db.Column(db.String(50))

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

        # Region-wise counts for bar chart
        regions = db.session.query(GeneralInformation.domain, db.func.count(GeneralInformation.sn)).group_by(GeneralInformation.domain).all()
        region_labels = [r[0] for r in regions if r[0] is not None]
        region_counts = [r[1] for r in regions if r[0] is not None]

        # Year-wise counts for pie chart (mocked as 2024/2025 split)
        total_exchanges = len(exchanges)
        year_counts = [total_exchanges // 2, total_exchanges - (total_exchanges // 2)]
        year_labels = ['2024', '2025']

        # Dashboard metrics
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
            # Auto-generate SN
            last_sn = db.session.query(db.func.max(GeneralInformation.sn)).scalar() or 0
            sn = last_sn + 1

            # Set domain based on user region
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
                latitude=float(request.form['latitude']) if request.form['latitude'] else None,
                longitude=float(request.form['longitude']) if request.form['longitude'] else None,
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
                load_of_individual_ne=float(request.form['load_of_individual_ne']) if request.form['load_of_individual_ne'] else None,
                name_of_nes_connected=request.form['name_of_nes_connected']
            )

            # Handle multiple rectifiers
            makes_of_rectifier = request.form.getlist('make_of_rectifier[]')
            for i in range(len(makes_of_rectifier)):
                if makes_of_rectifier[i]:
                    rectifier = Rectifier(
                        make_of_rectifier=makes_of_rectifier[i],
                        rectifier_capacity=float(request.form.getlist('rectifier_capacity[]')[i]) if request.form.getlist('rectifier_capacity[]')[i] else None,
                        no_of_modules=int(request.form.getlist('no_of_modules[]')[i]) if request.form.getlist('no_of_modules[]')[i] else None,
                        capacity_of_each_module=float(request.form.getlist('capacity_of_each_module[]')[i]) if request.form.getlist('capacity_of_each_module[]')[i] else None,
                        working_modules=int(request.form.getlist('working_modules[]')[i]) if request.form.getlist('working_modules[]')[i] else None,
                        faulty_modules=int(request.form.getlist('faulty_modules[]')[i]) if request.form.getlist('faulty_modules[]')[i] else None,
                        space_for_new_modules=int(request.form.getlist('space_for_new_modules[]')[i]) if request.form.getlist('space_for_new_modules[]')[i] else None,
                        grounding_of_rectifier='grounding_of_rectifier[]' in request.form and request.form.getlist('grounding_of_rectifier[]')[i] == 'on',
                        spd_in_rectifier='spd_in_rectifier[]' in request.form and request.form.getlist('spd_in_rectifier[]')[i] == 'on',
                        spd_model=request.form.getlist('spd_model[]')[i],
                        total_installed_spds=int(request.form.getlist('total_installed_spds[]')[i]) if request.form.getlist('total_installed_spds[]')[i] else None,
                        no_of_faulty_spds=int(request.form.getlist('no_of_faulty_spds[]')[i]) if request.form.getlist('no_of_faulty_spds[]')[i] else None
                    )
                    power_info.rectifiers.append(rectifier)

            general.power_info = power_info

            installed_dgs = request.form.getlist('installed_dg[]')
            for i in range(len(installed_dgs)):
                if installed_dgs[i]:
                    dg = DGInformation(
                        installed_dg=installed_dgs[i],
                        engine_make=request.form.getlist('engine_make[]')[i],
                        installation_year=int(request.form.getlist('installation_year[]')[i]) if request.form.getlist('installation_year[]')[i] else None,
                        dg_status=request.form.getlist('dg_status[]')[i],
                        dg_starting_battery=request.form.getlist('dg_starting_battery[]')[i],
                        smart_switch_installed='smart_switch_installed[]' in request.form and request.form.getlist('smart_switch_installed[]')[i] == 'on',
                        ats_installed='ats_installed[]' in request.form and request.form.getlist('ats_installed[]')[i] == 'on',
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

            locations = request.form.getlist('location_of_ac_unit[]')
            for i in range(len(locations)):
                if locations[i]:
                    ac = ACUnit(
                        location_of_ac_unit=locations[i],
                        working_status='working_status_ac[]' in request.form and request.form.getlist('working_status_ac[]')[i] == 'on',
                        ac_make=request.form.getlist('ac_make[]')[i],
                        capacity_tons=float(request.form.getlist('capacity_tons[]')[i]) if request.form.getlist('capacity_tons[]')[i] else None,
                        type_of_ac=request.form.getlist('type_of_ac[]')[i],
                        mount_type=request.form.getlist('mount_type[]')[i],
                        date_of_installation=request.form.getlist('date_of_installation_ac[]')[i],
                        sequence_controller_installed='sequence_controller_installed[]' in request.form and request.form.getlist('sequence_controller_installed[]')[i] == 'on',
                        ac_load=float(request.form.getlist('ac_load[]')[i]) if request.form.getlist('ac_load[]')[i] else None,
                        total_ac_load=float(request.form.getlist('total_ac_load[]')[i]) if request.form.getlist('total_ac_load[]')[i] else None,
                        fault_nature_of_ac_unit=request.form.getlist('fault_nature_of_ac_unit[]')[i],
                        estimate_to_repair_ac=float(request.form.getlist('estimate_to_repair_ac[]')[i]) if request.form.getlist('estimate_to_repair_ac[]')[i] else None
                    )
                    general.ac_units.append(ac)

            solar_info = SolarInformation(
                total_solar_size=float(request.form['total_solar_size']) if request.form['total_solar_size'] else None,
                pv_solar_panel_capacity=float(request.form['pv_solar_panel_capacity']) if request.form['pv_solar_panel_capacity'] else None,
                no_of_pv_panels_installed=int(request.form['no_of_pv_panels_installed']) if request.form['no_of_pv_panels_installed'] else None,
                make_of_pv_panels=request.form['make_of_pv_panels'],
                charge_controller_make=request.form['charge_controller_make']
            )
            general.solar_info = solar_info

            colocation_info = ColocationInformation(
                colocation='colocation' in request.form,
                name_of_colocation_vendors=request.form['name_of_colocation_vendors'],
                load_of_each_vendor=float(request.form['load_of_each_vendor']) if request.form['load_of_each_vendor'] else None,
                total_load=float(request.form['total_load']) if request.form['total_load'] else None
            )
            general.colocation_info = colocation_info

            building_info = BuildingInformation(
                building_type=request.form['building_type'],
                construction_year=int(request.form['construction_year']) if request.form['construction_year'] else None,
                total_area_sqft=float(request.form['total_area_sqft']) if request.form['total_area_sqft'] else None,
                number_of_floors=int(request.form['number_of_floors']) if request.form['number_of_floors'] else None,
                condition=request.form['condition']
            )
            general.building_info = building_info

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
            general.region = 'RTR'
            general.domain = request.form['domain'] if user_region == 'All' else user_region
            general.exchange_name = request.form['exchange_name']
            general.exchange_lic = request.form['exchange_lic']
            general.flc = request.form['flc']
            general.site_category = request.form['site_category']
            general.nes_installed = request.form['nes_installed']
            general.latitude = float(request.form['latitude']) if request.form['latitude'] else None
            general.longitude = float(request.form['longitude']) if request.form['longitude'] else None
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
            general.power_info.load_of_individual_ne = float(request.form['load_of_individual_ne']) if request.form['load_of_individual_ne'] else None
            general.power_info.name_of_nes_connected = request.form['name_of_nes_connected']

            general.power_info.rectifiers = []
            makes_of_rectifier = request.form.getlist('make_of_rectifier[]')
            for i in range(len(makes_of_rectifier)):
                if makes_of_rectifier[i]:
                    rectifier = Rectifier(
                        make_of_rectifier=makes_of_rectifier[i],
                        rectifier_capacity=float(request.form.getlist('rectifier_capacity[]')[i]) if request.form.getlist('rectifier_capacity[]')[i] else None,
                        no_of_modules=int(request.form.getlist('no_of_modules[]')[i]) if request.form.getlist('no_of_modules[]')[i] else None,
                        capacity_of_each_module=float(request.form.getlist('capacity_of_each_module[]')[i]) if request.form.getlist('capacity_of_each_module[]')[i] else None,
                        working_modules=int(request.form.getlist('working_modules[]')[i]) if request.form.getlist('working_modules[]')[i] else None,
                        faulty_modules=int(request.form.getlist('faulty_modules[]')[i]) if request.form.getlist('faulty_modules[]')[i] else None,
                        space_for_new_modules=int(request.form.getlist('space_for_new_modules[]')[i]) if request.form.getlist('space_for_new_modules[]')[i] else None,
                        grounding_of_rectifier='grounding_of_rectifier[]' in request.form and request.form.getlist('grounding_of_rectifier[]')[i] == 'on',
                        spd_in_rectifier='spd_in_rectifier[]' in request.form and request.form.getlist('spd_in_rectifier[]')[i] == 'on',
                        spd_model=request.form.getlist('spd_model[]')[i],
                        total_installed_spds=int(request.form.getlist('total_installed_spds[]')[i]) if request.form.getlist('total_installed_spds[]')[i] else None,
                        no_of_faulty_spds=int(request.form.getlist('no_of_faulty_spds[]')[i]) if request.form.getlist('no_of_faulty_spds[]')[i] else None
                    )
                    general.power_info.rectifiers.append(rectifier)

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
                        smart_switch_installed='smart_switch_installed[]' in request.form and request.form.getlist('smart_switch_installed[]')[i] == 'on',
                        ats_installed='ats_installed[]' in request.form and request.form.getlist('ats_installed[]')[i] == 'on',
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

            general.ac_units = []
            locations = request.form.getlist('location_of_ac_unit[]')
            for i in range(len(locations)):
                if locations[i]:
                    ac = ACUnit(
                        location_of_ac_unit=locations[i],
                        working_status='working_status_ac[]' in request.form and request.form.getlist('working_status_ac[]')[i] == 'on',
                        ac_make=request.form.getlist('ac_make[]')[i],
                        capacity_tons=float(request.form.getlist('capacity_tons[]')[i]) if request.form.getlist('capacity_tons[]')[i] else None,
                        type_of_ac=request.form.getlist('type_of_ac[]')[i],
                        mount_type=request.form.getlist('mount_type[]')[i],
                        date_of_installation=request.form.getlist('date_of_installation_ac[]')[i],
                        sequence_controller_installed='sequence_controller_installed[]' in request.form and request.form.getlist('sequence_controller_installed[]')[i] == 'on',
                        ac_load=float(request.form.getlist('ac_load[]')[i]) if request.form.getlist('ac_load[]')[i] else None,
                        total_ac_load=float(request.form.getlist('total_ac_load[]')[i]) if request.form.getlist('total_ac_load[]')[i] else None,
                        fault_nature_of_ac_unit=request.form.getlist('fault_nature_of_ac_unit[]')[i],
                        estimate_to_repair_ac=float(request.form.getlist('estimate_to_repair_ac[]')[i]) if request.form.getlist('estimate_to_repair_ac[]')[i] else None
                    )
                    general.ac_units.append(ac)

            if not general.solar_info:
                general.solar_info = SolarInformation()
            general.solar_info.total_solar_size = float(request.form['total_solar_size']) if request.form['total_solar_size'] else None
            general.solar_info.pv_solar_panel_capacity = float(request.form['pv_solar_panel_capacity']) if request.form['pv_solar_panel_capacity'] else None
            general.solar_info.no_of_pv_panels_installed = int(request.form['no_of_pv_panels_installed']) if request.form['no_of_pv_panels_installed'] else None
            general.solar_info.make_of_pv_panels = request.form['make_of_pv_panels']
            general.solar_info.charge_controller_make = request.form['charge_controller_make']

            if not general.colocation_info:
                general.colocation_info = ColocationInformation()
            general.colocation_info.colocation = 'colocation' in request.form
            general.colocation_info.name_of_colocation_vendors = request.form['name_of_colocation_vendors']
            general.colocation_info.load_of_each_vendor = float(request.form['load_of_each_vendor']) if request.form['load_of_each_vendor'] else None
            general.colocation_info.total_load = float(request.form['total_load']) if request.form['total_load'] else None

            if not general.building_info:
                general.building_info = BuildingInformation()
            general.building_info.building_type = request.form['building_type']
            general.building_info.construction_year = int(request.form['construction_year']) if request.form['construction_year'] else None
            general.building_info.total_area_sqft = float(request.form['total_area_sqft']) if request.form['total_area_sqft'] else None
            general.building_info.number_of_floors = int(request.form['number_of_floors']) if request.form['number_of_floors'] else None
            general.building_info.condition = request.form['condition']

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

            for i, tower in enumerate(exchange.towers, 1):
                row[f'Tower {i} Type/Height'] = tower.tower_type_height

            if exchange.power_info:
                row.update({
                    'WAPDA Ref Number': exchange.power_info.wapda_ref_number,
                    'Transformer Capacity': exchange.power_info.transformer_capacity,
                    'Transformer Earthing': exchange.power_info.transformer_earthing,
                    'Working Status (Power)': exchange.power_info.working_status,
                    'Name of NEs Connected': exchange.power_info.name_of_nes_connected,
                    'Load of Individual NE': exchange.power_info.load_of_individual_ne
                })

            for i, rectifier in enumerate(exchange.power_info.rectifiers, 1):
                row.update({
                    f'Rectifier {i} Make': rectifier.make_of_rectifier,
                    f'Rectifier {i} Capacity': rectifier.rectifier_capacity,
                    f'Rectifier {i} No of Modules': rectifier.no_of_modules,
                    f'Rectifier {i} Capacity of Each Module': rectifier.capacity_of_each_module,
                    f'Rectifier {i} Working Modules': rectifier.working_modules,
                    f'Rectifier {i} Faulty Modules': rectifier.faulty_modules,
                    f'Rectifier {i} Space for New Modules': rectifier.space_for_new_modules,
                    f'Rectifier {i} Grounding': rectifier.grounding_of_rectifier,
                    f'Rectifier {i} SPD Installed': rectifier.spd_in_rectifier,
                    f'Rectifier {i} SPD Model': rectifier.spd_model,
                    f'Rectifier {i} Total Installed SPDs': rectifier.total_installed_spds,
                    f'Rectifier {i} No of Faulty SPDs': rectifier.no_of_faulty_spds
                })

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

            if exchange.solar_info:
                row.update({
                    'Total Solar Size': exchange.solar_info.total_solar_size,
                    'PV Solar Panel Capacity': exchange.solar_info.pv_solar_panel_capacity,
                    'No of PV Panels Installed': exchange.solar_info.no_of_pv_panels_installed,
                    'Make of PV Panels': exchange.solar_info.make_of_pv_panels,
                    'Charge Controller Make': exchange.solar_info.charge_controller_make
                })

            if exchange.colocation_info:
                row.update({
                    'Colocation': exchange.colocation_info.colocation,
                    'Name of Colocation Vendors': exchange.colocation_info.name_of_colocation_vendors,
                    'Load of Each Vendor': exchange.colocation_info.load_of_each_vendor,
                    'Total Load': exchange.colocation_info.total_load
                })

            if exchange.building_info:
                row.update({
                    'Building Type': exchange.building_info.building_type,
                    'Construction Year': exchange.building_info.construction_year,
                    'Total Area (sqft)': exchange.building_info.total_area_sqft,
                    'Number of Floors': exchange.building_info.number_of_floors,
                    'Condition': exchange.building_info.condition
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
        exchanges = GeneralInformation.query.filter_by(domain=user_region).all()
    return render_template('view_exchanges.html', exchanges=exchanges)

if __name__ == '__main__':
    app.run(debug=True)