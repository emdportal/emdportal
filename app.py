from flask import Flask, render_template, request, redirect, url_for, flash, send_file, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import pandas as pd
import io
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from functools import wraps
import secrets

# Load environment variables from .env file (for local development)
load_dotenv()

app = Flask(__name__)
# Use PostgreSQL DATABASE_URL from Railway, fallback to SQLite for local dev
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///exchanges.db').replace('postgres://', 'postgresql://')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Secure SECRET_KEY via environment variable, generate a secure default if not set
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(16))
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Secure Supabase setup
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Models (User model removed, now handled by Supabase)
class GeneralInformation(db.Model):
    sn = db.Column(db.Integer, primary_key=True)
    region = db.Column(db.String(100))
    domain = db.Column(db.String(100))
    exchange_name = db.Column(db.String(100))
    exchange_lic = db.Column(db.String(100))
    flc = db.Column(db.String(100))
    site_category = db.Column(db.String(100))
    nes_installed = db.Column(db.Text)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    tower_available = db.Column(db.String(3))  # 'Yes' or 'No'
    towers = db.relationship('Tower', backref='general', cascade="all, delete-orphan")
    power_info = db.relationship('PowerInformation', backref='general', uselist=False, cascade="all, delete-orphan")
    dgs = db.relationship('DG', backref='general', cascade="all, delete-orphan")
    battery_banks = db.relationship('BatteryBank', backref='general', cascade="all, delete-orphan")
    ac_units = db.relationship('ACUnit', backref='general', cascade="all, delete-orphan")
    solar_info = db.relationship('InstalledSolarInformation', backref='general', uselist=False, cascade="all, delete-orphan")
    earthing = db.relationship('Earthing', backref='general', uselist=False, cascade="all, delete-orphan")
    fire_extinguishers = db.relationship('FireExtinguisher', backref='general', cascade="all, delete-orphan")
    pmr_info = db.relationship('PMRInformation', backref='general', uselist=False, cascade="all, delete-orphan")
    alarm_extension = db.relationship('AlarmExtension', backref='general', uselist=False, cascade="all, delete-orphan")
    colocation_info = db.relationship('ColocationInformation', backref='general', uselist=False, cascade="all, delete-orphan")
    building_info = db.relationship('BuildingInformation', backref='general', uselist=False, cascade="all, delete-orphan")

class Tower(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn'), nullable=False)
    tower_type_height = db.Column(db.String(100))

class PowerInformation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn'), nullable=False)
    wapda_ref_number = db.Column(db.String(100))
    transformer_capacity = db.Column(db.String(100))
    transformer_earthing = db.Column(db.String(100))
    make_of_rectifier = db.Column(db.String(100))
    working_status = db.Column(db.Boolean, default=False)
    rectifier_capacity = db.Column(db.Float)
    no_of_modules = db.Column(db.Integer)
    capacity_of_each_module = db.Column(db.Float)
    working_modules = db.Column(db.Integer)
    faulty_modules = db.Column(db.Integer)
    space_for_new_modules = db.Column(db.Integer)
    name_of_nes_connected = db.Column(db.Text)
    load_of_individual_ne = db.Column(db.Float)
    grounding_of_rectifier = db.Column(db.Boolean, default=False)
    spd_in_rectifier = db.Column(db.Boolean, default=False)
    spd_model = db.Column(db.String(100))
    total_installed_spds = db.Column(db.Integer)
    no_of_faulty_spds = db.Column(db.Integer)

class DG(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn'), nullable=False)
    installed_dg = db.Column(db.String(100))
    engine_make = db.Column(db.String(100))
    installation_year = db.Column(db.Integer)
    dg_status = db.Column(db.String(50))  # Working, Faulty, Spare
    dg_starting_battery = db.Column(db.String(100))
    smart_switch_installed = db.Column(db.Boolean, default=False)
    ats_installed = db.Column(db.Boolean, default=False)
    ats_capacity = db.Column(db.String(100))
    name_of_faulty_ats_parts = db.Column(db.String(200))
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
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn'), nullable=False)
    make_of_battery = db.Column(db.String(100))
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
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn'), nullable=False)
    location_of_ac_unit = db.Column(db.String(100))
    working_status = db.Column(db.Boolean, default=False)
    ac_make = db.Column(db.String(100))
    capacity_tons = db.Column(db.Float)
    type_of_ac = db.Column(db.String(50))
    mount_type = db.Column(db.String(50))
    date_of_installation = db.Column(db.String(50))
    sequence_controller_installed = db.Column(db.Boolean, default=False)
    ac_load = db.Column(db.Float)
    total_ac_load = db.Column(db.Float)
    fault_nature_of_ac_unit = db.Column(db.String(200))
    estimate_to_repair_ac = db.Column(db.Float)

class InstalledSolarInformation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn'), nullable=False)
    total_solar_size = db.Column(db.Float)
    pv_solar_panel_capacity = db.Column(db.Float)
    no_of_pv_panels_installed = db.Column(db.Integer)
    make_of_pv_panels = db.Column(db.String(100))
    charge_controller_make = db.Column(db.String(100))
    no_of_charge_controllers = db.Column(db.Integer)
    charge_controller_capacity = db.Column(db.Float)
    inverter_make = db.Column(db.String(100))
    inverter_capacity = db.Column(db.Float)
    no_of_inverters = db.Column(db.Integer)
    on_grid_hybrid = db.Column(db.String(50))
    roof_top_ground = db.Column(db.String(50))

class Earthing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn'), nullable=False)
    earthing_value = db.Column(db.Float)
    no_of_pits = db.Column(db.Integer)

class FireExtinguisher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn'), nullable=False)
    fe MIGRAinstalled = db.Column(db.Boolean, default=False)
    no_of_fes = db.Column(db.Integer)
    type_of_gas = db.Column(db.String(100))
    date_of_expiry = db.Column(db.String(50))

class PMRInformation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn'), nullable=False)
    pmr_performed = db.Column(db.Boolean, default=False)
    last_performed_date = db.Column(db.String(50))

class AlarmExtension(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn'), nullable=False)
    ac_main_failure = db.Column(db.Boolean, default=False)
    dc_low_voltages = db.Column(db.Boolean, default=False)
    rectifier_failure = db.Column(db.Boolean, default=False)

class ColocationInformation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn'), nullable=False)
    colocation = db.Column(db.Boolean, default=False)
    name_of_colocation_vendors = db.Column(db.Text)
    load_of_each_vendor = db.Column(db.Float)
    total_load = db.Column(db.Float)

class BuildingInformation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    general_id = db.Column(db.Integer, db.ForeignKey('general_information.sn'), nullable=False)
    building_status = db.Column(db.String(50))
    wall_doors_condition = db.Column(db.String(100))

# Custom decorator for Supabase authentication
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_token = request.cookies.get('auth_token')
        if not auth_token:
            return redirect(url_for('login'))
        try:
            user = supabase.auth.get_user(auth_token)
            if not user:
                return redirect(url_for('login'))
        except Exception:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Authenticate with Supabase (assuming usernames are email-like)
        try:
            response = supabase.auth.sign_in_with_password({"email": f"{username}@example.com", "password": password})
            if response.user:
                access_token = response.session.access_token
                # Set secure cookie with access token
                resp = make_response(redirect(url_for('index')))
                resp.set_cookie('auth_token', access_token, httponly=True, secure=True, samesite='Lax')
                return resp
            else:
                flash('Invalid username or password')
        except Exception as e:
            flash('Login failed: ' + str(e))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    resp = make_response(redirect(url_for('login')))
    resp.set_cookie('auth_token', '', expires=0)  # Clear the cookie
    supabase.auth.sign_out()  # Sign out from Supabase
    return resp

@app.route('/')
@login_required
def index():
    exchanges = GeneralInformation.query.all()
    regions = db.session.query(GeneralInformation.region, db.func.count(GeneralInformation.sn)).group_by(GeneralInformation.region).all()
    region_labels = [r[0] for r in regions if r[0] is not None]
    region_counts = [r[1] for r in regions if r[0] is not None]
    total_exchanges = len(exchanges)
    year_counts = [total_exchanges // 2, total_exchanges - (total_exchanges // 2)]
    return render_template('index.html', exchanges=exchanges, region_labels=region_labels, region_counts=region_counts, year_counts=year_counts)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        sn = request.form.get('sn')
        region = request.form.get('region')
        if GeneralInformation.query.filter_by(sn=sn).first():
            flash('Exchange with this SN already exists!')
            return redirect(url_for('add'))
        new_exchange = GeneralInformation(
            sn=sn,
            region=region,
            domain=request.form.get('domain'),
            exchange_name=request.form.get('exchange_name'),
            exchange_lic=request.form.get('exchange_lic'),
            flc=request.form.get('flc'),
            site_category=request.form.get('site_category'),
            nes_installed=request.form.get('nes_installed'),
            latitude=float(request.form.get('latitude')) if request.form.get('latitude') else None,
            longitude=float(request.form.get('longitude')) if request.form.get('longitude') else None,
            tower_available=request.form.get('tower_available')
        )
        # Towers
        tower_type_heights = request.form.getlist('tower_type_height[]')
        if new_exchange.tower_available == 'Yes':
            for tower_type_height in tower_type_heights:
                if tower_type_height:
                    tower = Tower(tower_type_height=tower_type_height)
                    new_exchange.towers.append(tower)
        # Power Information
        power_info = PowerInformation(
            wapda_ref_number=request.form.get('wapda_ref_number'),
            transformer_capacity=request.form.get('transformer_capacity'),
            transformer_earthing=request.form.get('transformer_earthing'),
            make_of_rectifier=request.form.get('make_of_rectifier'),
            working_status='working_status_power' in request.form,
            rectifier_capacity=float(request.form.get('rectifier_capacity')) if request.form.get('rectifier_capacity') else None,
            no_of_modules=int(request.form.get('no_of_modules')) if request.form.get('no_of_modules') else None,
            capacity_of_each_module=float(request.form.get('capacity_of_each_module')) if request.form.get('capacity_of_each_module') else None,
            working_modules=int(request.form.get('working_modules')) if request.form.get('working_modules') else None,
            faulty_modules=int(request.form.get('faulty_modules')) if request.form.get('faulty_modules') else None,
            space_for_new_modules=int(request.form.get('space_for_new_modules')) if request.form.get('space_for_new_modules') else None,
            name_of_nes_connected=request.form.get('name_of_nes_connected'),
            load_of_individual_ne=float(request.form.get('load_of_individual_ne')) if request.form.get('load_of_individual_ne') else None,
            grounding_of_rectifier='grounding_of_rectifier' in request.form,
            spd_in_rectifier='spd_in_rectifier' in request.form,
            spd_model=request.form.get('spd_model'),
            total_installed_spds=int(request.form.get('total_installed_spds')) if request.form.get('total_installed_spds') else None,
            no_of_faulty_spds=int(request.form.get('no_of_faulty_spds')) if request.form.get('no_of_faulty_spds') else None
        )
        new_exchange.power_info = power_info
        # DGs
        installed_dgs = request.form.getlist('installed_dg[]')
        engine_makes = request.form.getlist('engine_make[]')
        installation_years = request.form.getlist('installation_year[]')
        dg_statuses = request.form.getlist('dg_status[]')
        dg_starting_batteries = request.form.getlist('dg_starting_battery[]')
        smart_switch_installeds = request.form.getlist('smart_switch_installed[]')
        ats_installeds = request.form.getlist('ats_installed[]')
        ats_capacities = request.form.getlist('ats_capacity[]')
        name_of_faulty_ats_parts_list = request.form.getlist('name_of_faulty_ats_parts[]')
        no_of_faulty_ats_parts_list = request.form.getlist('no_of_faulty_ats_parts[]')
        load_on_dg_p1s = request.form.getlist('load_on_dg_p1[]')
        load_on_dg_p2s = request.form.getlist('load_on_dg_p2[]')
        load_on_dg_p3s = request.form.getlist('load_on_dg_p3[]')
        site_load_totals = request.form.getlist('site_load_total[]')
        site_load_p1s = request.form.getlist('site_load_p1[]')
        site_load_p2s = request.form.getlist('site_load_p2[]')
        site_load_p3s = request.form.getlist('site_load_p3[]')
        for i in range(len(installed_dgs)):
            if installed_dgs[i]:
                dg = DG(
                    installed_dg=installed_dgs[i],
                    engine_make=engine_makes[i],
                    installation_year=int(installation_years[i]) if installation_years[i] else None,
                    dg_status=dg_statuses[i],
                    dg_starting_battery=dg_starting_batteries[i],
                    smart_switch_installed=f'smart_switch_installed_{i}' in request.form,
                    ats_installed=f'ats_installed_{i}' in request.form,
                    ats_capacity=ats_capacities[i],
                    name_of_faulty_ats_parts=name_of_faulty_ats_parts_list[i],
                    no_of_faulty_ats_parts=int(no_of_faulty_ats_parts_list[i]) if no_of_faulty_ats_parts_list[i] else None,
                    load_on_dg_p1=float(load_on_dg_p1s[i]) if load_on_dg_p1s[i] else None,
                    load_on_dg_p2=float(load_on_dg_p2s[i]) if load_on_dg_p2s[i] else None,
                    load_on_dg_p3=float(load_on_dg_p3s[i]) if load_on_dg_p3s[i] else None,
                    site_load_total=float(site_load_totals[i]) if site_load_totals[i] else None,
                    site_load_p1=float(site_load_p1s[i]) if site_load_p1s[i] else None,
                    site_load_p2=float(site_load_p2s[i]) if site_load_p2s[i] else None,
                    site_load_p3=float(site_load_p3s[i]) if site_load_p3s[i] else None
                )
                new_exchange.dgs.append(dg)
        # Battery Banks
        make_of_batteries = request.form.getlist('make_of_battery[]')
        battery_capacities = request.form.getlist('battery_capacity[]')
        battery_types = request.form.getlist('battery_type[]')
        no_of_cells_banks = request.form.getlist('no_of_cells_bank[]')
        date_of_installations_battery = request.form.getlist('date_of_installation_battery[]')
        load_on_battery_banks = request.form.getlist('load_on_battery_bank[]')
        practical_backup_times = request.form.getlist('practical_backup_time[]')
        battery_installed_new_or_useds = request.form.getlist('battery_installed_new_or_used[]')
        battery_moved_froms = request.form.getlist('battery_moved_from[]')
        for i in range(len(make_of_batteries)):
            if make_of_batteries[i]:
                battery = BatteryBank(
                    make_of_battery=make_of_batteries[i],
                    battery_capacity=float(battery_capacities[i]) if battery_capacities[i] else None,
                    battery_type=battery_types[i],
                    no_of_cells_bank=int(no_of_cells_banks[i]) if no_of_cells_banks[i] else None,
                    date_of_installation=date_of_installations_battery[i],
                    load_on_battery_bank=float(load_on_battery_banks[i]) if load_on_battery_banks[i] else None,
                    practical_backup_time=float(practical_backup_times[i]) if practical_backup_times[i] else None,
                    battery_installed_new_or_used=battery_installed_new_or_useds[i],
                    battery_moved_from=battery_moved_froms[i]
                )
                new_exchange.battery_banks.append(battery)
        # AC Units
        location_of_ac_units = request.form.getlist('location_of_ac_unit[]')
        working_status_acs = request.form.getlist('working_status_ac[]')
        ac_makes = request.form.getlist('ac_make[]')
        capacity_tons_list = request.form.getlist('capacity_tons[]')
        type_of_acs = request.form.getlist('type_of_ac[]')
        mount_types = request.form.getlist('mount_type[]')
        date_of_installations_ac = request.form.getlist('date_of_installation_ac[]')
        sequence_controller_installeds = request.form.getlist('sequence_controller_installed[]')
        ac_loads = request.form.getlist('ac_load[]')
        total_ac_loads = request.form.getlist('total_ac_load[]')
        fault_nature_of_ac_units = request.form.getlist('fault_nature_of_ac_unit[]')
        estimate_to_repair_acs = request.form.getlist('estimate_to_repair_ac[]')
        for i in range(len(location_of_ac_units)):
            if location_of_ac_units[i]:
                ac_unit = ACUnit(
                    location_of_ac_unit=location_of_ac_units[i],
                    working_status=f'working_status_ac_{i}' in request.form,
                    ac_make=ac_makes[i],
                    capacity_tons=float(capacity_tons_list[i]) if capacity_tons_list[i] else None,
                    type_of_ac=type_of_acs[i],
                    mount_type=mount_types[i],
                    date_of_installation=date_of_installations_ac[i],
                    sequence_controller_installed=f'sequence_controller_installed_{i}' in request.form,
                    ac_load=float(ac_loads[i]) if ac_loads[i] else None,
                    total_ac_load=float(total_ac_loads[i]) if total_ac_loads[i] else None,
                    fault_nature_of_ac_unit=fault_nature_of_ac_units[i],
                    estimate_to_repair_ac=float(estimate_to_repair_acs[i]) if estimate_to_repair_acs[i] else None
                )
                new_exchange.ac_units.append(ac_unit)
        # Solar Information
        solar_info = InstalledSolarInformation(
            total_solar_size=float(request.form.get('total_solar_size')) if request.form.get('total_solar_size') else None,
            pv_solar_panel_capacity=float(request.form.get('pv_solar_panel_capacity')) if request.form.get('pv_solar_panel_capacity') else None,
            no_of_pv_panels_installed=int(request.form.get('no_of_pv_panels_installed')) if request.form.get('no_of_pv_panels_installed') else None,
            make_of_pv_panels=request.form.get('make_of_pv_panels'),
            charge_controller_make=request.form.get('charge_controller_make'),
            no_of_charge_controllers=int(request.form.get('no_of_charge_controllers')) if request.form.get('no_of_charge_controllers') else None,
            charge_controller_capacity=float(request.form.get('charge_controller_capacity')) if request.form.get('charge_controller_capacity') else None,
            inverter_make=request.form.get('inverter_make'),
            inverter_capacity=float(request.form.get('inverter_capacity')) if request.form.get('inverter_capacity') else None,
            no_of_inverters=int(request.form.get('no_of_inverters')) if request.form.get('no_of_inverters') else None,
            on_grid_hybrid=request.form.get('on_grid_hybrid'),
            roof_top_ground=request.form.get('roof_top_ground')
        )
        new_exchange.solar_info = solar_info
        # Earthing
        earthing = Earthing(
            earthing_value=float(request.form.get('earthing_value')) if request.form.get('earthing_value') else None,
            no_of_pits=int(request.form.get('no_of_pits')) if request.form.get('no_of_pits') else None
        )
        new_exchange.earthing = earthing
        # Fire Extinguishers
        fe_installeds = request.form.getlist('fe_installed[]')
        no_of_fes_list = request.form.getlist('no_of_fes[]')
        type_of_gases = request.form.getlist('type_of_gas[]')
        date_of_expiries = request.form.getlist('date_of_expiry[]')
        for i in range(len(fe_installeds)):
            if fe_installeds[i]:
                fire_extinguisher = FireExtinguisher(
                    fe_installed=f'fe_installed_{i}' in request.form,
                    no_of_fes=int(no_of_fes_list[i]) if no_of_fes_list[i] else None,
                    type_of_gas=type_of_gases[i],
                    date_of_expiry=date_of_expiries[i]
                )
                new_exchange.fire_extinguishers.append(fire_extinguisher)
        # PMR Information
        pmr_info = PMRInformation(
            pmr_performed='pmr_performed' in request.form,
            last_performed_date=request.form.get('last_performed_date')
        )
        new_exchange.pmr_info = pmr_info
        # Alarm Extension
        alarm_extension = AlarmExtension(
            ac_main_failure='ac_main_failure' in request.form,
            dc_low_voltages='dc_low_voltages' in request.form,
            rectifier_failure='rectifier_failure' in request.form
        )
        new_exchange.alarm_extension = alarm_extension
        # Colocation Information
        colocation_info = ColocationInformation(
            colocation='colocation' in request.form,
            name_of_colocation_vendors=request.form.get('name_of_colocation_vendors'),
            load_of_each_vendor=float(request.form.get('load_of_each_vendor')) if request.form.get('load_of_each_vendor') else None,
            total_load=float(request.form.get('total_load')) if request.form.get('total_load') else None
        )
        new_exchange.colocation_info = colocation_info
        # Building Information
        building_info = BuildingInformation(
            building_status=request.form.get('building_status'),
            wall_doors_condition=request.form.get('wall_doors_condition')
        )
        new_exchange.building_info = building_info
        db.session.add(new_exchange)
        db.session.commit()
        flash('Exchange added successfully!')
        return redirect(url_for('index'))
    return render_template('form.html')

@app.route('/edit/<int:sn>', methods=['GET', 'POST'])
@login_required
def edit(sn):
    exchange = GeneralInformation.query.get_or_404(sn)
    if request.method == 'POST':
        exchange.region = request.form.get('region')
        exchange.domain = request.form.get('domain')
        exchange.exchange_name = request.form.get('exchange_name')
        exchange.exchange_lic = request.form.get('exchange_lic')
        exchange.flc = request.form.get('flc')
        exchange.site_category = request.form.get('site_category')
        exchange.nes_installed = request.form.get('nes_installed')
        exchange.latitude = float(request.form.get('latitude')) if request.form.get('latitude') else None
        exchange.longitude = float(request.form.get('longitude')) if request.form.get('longitude') else None
        exchange.tower_available = request.form.get('tower_available')
        # Update Towers
        tower_type_heights = request.form.getlist('tower_type_height[]')
        db.session.query(Tower).filter_by(general_id=exchange.sn).delete()
        if exchange.tower_available == 'Yes':
            for tower_type_height in tower_type_heights:
                if tower_type_height:
                    tower = Tower(tower_type_height=tower_type_height, general_id=exchange.sn)
                    db.session.add(tower)
        # Update Power Information
        exchange.power_info.wapda_ref_number = request.form.get('wapda_ref_number')
        exchange.power_info.transformer_capacity = request.form.get('transformer_capacity')
        exchange.power_info.transformer_earthing = request.form.get('transformer_earthing')
        exchange.power_info.make_of_rectifier = request.form.get('make_of_rectifier')
        exchange.power_info.working_status = 'working_status_power' in request.form
        exchange.power_info.rectifier_capacity = float(request.form.get('rectifier_capacity')) if request.form.get('rectifier_capacity') else None
        exchange.power_info.no_of_modules = int(request.form.get('no_of_modules')) if request.form.get('no_of_modules') else None
        exchange.power_info.capacity_of_each_module = float(request.form.get('capacity_of_each_module')) if request.form.get('capacity_of_each_module') else None
        exchange.power_info.working_modules = int(request.form.get('working_modules')) if request.form.get('working_modules') else None
        exchange.power_info.faulty_modules = int(request.form.get('faulty_modules')) if request.form.get('faulty_modules') else None
        exchange.power_info.space_for_new_modules = int(request.form.get('space_for_new_modules')) if request.form.get('space_for_new_modules') else None
        exchange.power_info.name_of_nes_connected = request.form.get('name_of_nes_connected')
        exchange.power_info.load_of_individual_ne = float(request.form.get('load_of_individual_ne')) if request.form.get('load_of_individual_ne') else None
        exchange.power_info.grounding_of_rectifier = 'grounding_of_rectifier' in request.form
        exchange.power_info.spd_in_rectifier = 'spd_in_rectifier' in request.form
        exchange.power_info.spd_model = request.form.get('spd_model')
        exchange.power_info.total_installed_spds = int(request.form.get('total_installed_spds')) if request.form.get('total_installed_spds') else None
        exchange.power_info.no_of_faulty_spds = int(request.form.get('no_of_faulty_spds')) if request.form.get('no_of_faulty_spds') else None
        # Update DGs
        db.session.query(DG).filter_by(general_id=exchange.sn).delete()
        installed_dgs = request.form.getlist('installed_dg[]')
        engine_makes = request.form.getlist('engine_make[]')
        installation_years = request.form.getlist('installation_year[]')
        dg_statuses = request.form.getlist('dg_status[]')
        dg_starting_batteries = request.form.getlist('dg_starting_battery[]')
        smart_switch_installeds = request.form.getlist('smart_switch_installed[]')
        ats_installeds = request.form.getlist('ats_installed[]')
        ats_capacities = request.form.getlist('ats_capacity[]')
        name_of_faulty_ats_parts_list = request.form.getlist('name_of_faulty_ats_parts[]')
        no_of_faulty_ats_parts_list = request.form.getlist('no_of_faulty_ats_parts[]')
        load_on_dg_p1s = request.form.getlist('load_on_dg_p1[]')
        load_on_dg_p2s = request.form.getlist('load_on_dg_p2[]')
        load_on_dg_p3s = request.form.getlist('load_on_dg_p3[]')
        site_load_totals = request.form.getlist('site_load_total[]')
        site_load_p1s = request.form.getlist('site_load_p1[]')
        site_load_p2s = request.form.getlist('site_load_p2[]')
        site_load_p3s = request.form.getlist('site_load_p3[]')
        for i in range(len(installed_dgs)):
            if installed_dgs[i]:
                dg = DG(
                    installed_dg=installed_dgs[i],
                    engine_make=engine_makes[i],
                    installation_year=int(installation_years[i]) if installation_years[i] else None,
                    dg_status=dg_statuses[i],
                    dg_starting_battery=dg_starting_batteries[i],
                    smart_switch_installed=f'smart_switch_installed_{i}' in request.form,
                    ats_installed=f'ats_installed_{i}' in request.form,
                    ats_capacity=ats_capacities[i],
                    name_of_faulty_ats_parts=name_of_faulty_ats_parts_list[i],
                    no_of_faulty_ats_parts=int(no_of_faulty_ats_parts_list[i]) if no_of_faulty_ats_parts_list[i] else None,
                    load_on_dg_p1=float(load_on_dg_p1s[i]) if load_on_dg_p1s[i] else None,
                    load_on_dg_p2=float(load_on_dg_p2s[i]) if load_on_dg_p2s[i] else None,
                    load_on_dg_p3=float(load_on_dg_p3s[i]) if load_on_dg_p3s[i] else None,
                    site_load_total=float(site_load_totals[i]) if site_load_totals[i] else None,
                    site_load_p1=float(site_load_p1s[i]) if site_load_p1s[i] else None,
                    site_load_p2=float(site_load_p2s[i]) if site_load_p2s[i] else None,
                    site_load_p3=float(site_load_p3s[i]) if site_load_p3s[i] else None,
                    general_id=exchange.sn
                )
                db.session.add(dg)
        # Update Battery Banks
        db.session.query(BatteryBank).filter_by(general_id=exchange.sn).delete()
        make_of_batteries = request.form.getlist('make_of_battery[]')
        battery_capacities = request.form.getlist('battery_capacity[]')
        battery_types = request.form.getlist('battery_type[]')
        no_of_cells_banks = request.form.getlist('no_of_cells_bank[]')
        date_of_installations_battery = request.form.getlist('date_of_installation_battery[]')
        load_on_battery_banks = request.form.getlist('load_on_battery_bank[]')
        practical_backup_times = request.form.getlist('practical_backup_time[]')
        battery_installed_new_or_useds = request.form.getlist('battery_installed_new_or_used[]')
        battery_moved_froms = request.form.getlist('battery_moved_from[]')
        for i in range(len(make_of_batteries)):
            if make_of_batteries[i]:
                battery = BatteryBank(
                    make_of_battery=make_of_batteries[i],
                    battery_capacity=float(battery_capacities[i]) if battery_capacities[i] else None,
                    battery_type=battery_types[i],
                    no_of_cells_bank=int(no_of_cells_banks[i]) if no_of_cells_banks[i] else None,
                    date_of_installation=date_of_installations_battery[i],
                    load_on_battery_bank=float(load_on_battery_banks[i]) if load_on_battery_banks[i] else None,
                    practical_backup_time=float(practical_backup_times[i]) if practical_backup_times[i] else None,
                    battery_installed_new_or_used=battery_installed_new_or_useds[i],
                    battery_moved_from=battery_moved_froms[i],
                    general_id=exchange.sn
                )
                db.session.add(battery)
        # Update AC Units
        db.session.query(ACUnit).filter_by(general_id=exchange.sn).delete()
        location_of_ac_units = request.form.getlist('location_of_ac_unit[]')
        working_status_acs = request.form.getlist('working_status_ac[]')
        ac_makes = request.form.getlist('ac_make[]')
        capacity_tons_list = request.form.getlist('capacity_tons[]')
        type_of_acs = request.form.getlist('type_of_ac[]')
        mount_types = request.form.getlist('mount_type[]')
        date_of_installations_ac = request.form.getlist('date_of_installation_ac[]')
        sequence_controller_installeds = request.form.getlist('sequence_controller_installed[]')
        ac_loads = request.form.getlist('ac_load[]')
        total_ac_loads = request.form.getlist('total_ac_load[]')
        fault_nature_of_ac_units = request.form.getlist('fault_nature_of_ac_unit[]')
        estimate_to_repair_acs = request.form.getlist('estimate_to_repair_ac[]')
        for i in range(len(location_of_ac_units)):
            if location_of_ac_units[i]:
                ac_unit = ACUnit(
                    location_of_ac_unit=location_of_ac_units[i],
                    working_status=f'working_status_ac_{i}' in request.form,
                    ac_make=ac_makes[i],
                    capacity_tons=float(capacity_tons_list[i]) if capacity_tons_list[i] else None,
                    type_of_ac=type_of_acs[i],
                    mount_type=mount_types[i],
                    date_of_installation=date_of_installations_ac[i],
                    sequence_controller_installed=f'sequence_controller_installed_{i}' in request.form,
                    ac_load=float(ac_loads[i]) if ac_loads[i] else None,
                    total_ac_load=float(total_ac_loads[i]) if total_ac_loads[i] else None,
                    fault_nature_of_ac_unit=fault_nature_of_ac_units[i],
                    estimate_to_repair_ac=float(estimate_to_repair_acs[i]) if estimate_to_repair_acs[i] else None,
                    general_id=exchange.sn
                )
                db.session.add(ac_unit)
        # Update Solar Information
        exchange.solar_info.total_solar_size = float(request.form.get('total_solar_size')) if request.form.get('total_solar_size') else None
        exchange.solar_info.pv_solar_panel_capacity = float(request.form.get('pv_solar_panel_capacity')) if request.form.get('pv_solar_panel_capacity') else None
        exchange.solar_info.no_of_pv_panels_installed = int(request.form.get('no_of_pv_panels_installed')) if request.form.get('no_of_pv_panels_installed') else None
        exchange.solar_info.make_of_pv_panels = request.form.get('make_of_pv_panels')
        exchange.solar_info.charge_controller_make = request.form.get('charge_controller_make')
        exchange.solar_info.no_of_charge_controllers = int(request.form.get('no_of_charge_controllers')) if request.form.get('no_of_charge_controllers') else None
        exchange.solar_info.charge_controller_capacity = float(request.form.get('charge_controller_capacity')) if request.form.get('charge_controller_capacity') else None
        exchange.solar_info.inverter_make = request.form.get('inverter_make')
        exchange.solar_info.inverter_capacity = float(request.form.get('inverter_capacity')) if request.form.get('inverter_capacity') else None
        exchange.solar_info.no_of_inverters = int(request.form.get('no_of_inverters')) if request.form.get('no_of_inverters') else None
        exchange.solar_info.on_grid_hybrid = request.form.get('on_grid_hybrid')
        exchange.solar_info.roof_top_ground = request.form.get('roof_top_ground')
        # Update Earthing
        exchange.earthing.earthing_value = float(request.form.get('earthing_value')) if request.form.get('earthing_value') else None
        exchange.earthing.no_of_pits = int(request.form.get('no_of_pits')) if request.form.get('no_of_pits') else None
        # Update Fire Extinguishers
        db.session.query(FireExtinguisher).filter_by(general_id=exchange.sn).delete()
        fe_installeds = request.form.getlist('fe_installed[]')
        no_of_fes_list = request.form.getlist('no_of_fes[]')
        type_of_gases = request.form.getlist('type_of_gas[]')
        date_of_expiries = request.form.getlist('date_of_expiry[]')
        for i in range(len(fe_installeds)):
            if fe_installeds[i]:
                fire_extinguisher = FireExtinguisher(
                    fe_installed=f'fe_installed_{i}' in request.form,
                    no_of_fes=int(no_of_fes_list[i]) if no_of_fes_list[i] else None,
                    type_of_gas=type_of_gases[i],
                    date_of_expiry=date_of_expiries[i],
                    general_id=exchange.sn
                )
                db.session.add(fire_extinguisher)
        # Update PMR Information
        exchange.pmr_info.pmr_performed = 'pmr_performed' in request.form
        exchange.pmr_info.last_performed_date = request.form.get('last_performed_date')
        # Update Alarm Extension
        exchange.alarm_extension.ac_main_failure = 'ac_main_failure' in request.form
        exchange.alarm_extension.dc_low_voltages = 'dc_low_voltages' in request.form
        exchange.alarm_extension.rectifier_failure = 'rectifier_failure' in request.form
        # Update Colocation Information
        exchange.colocation_info.colocation = 'colocation' in request.form
        exchange.colocation_info.name_of_colocation_vendors = request.form.get('name_of_colocation_vendors')
        exchange.colocation_info.load_of_each_vendor = float(request.form.get('load_of_each_vendor')) if request.form.get('load_of_each_vendor') else None
        exchange.colocation_info.total_load = float(request.form.get('total_load')) if request.form.get('total_load') else None
        # Update Building Information
        exchange.building_info.building_status = request.form.get('building_status')
        exchange.building_info.wall_doors_condition = request.form.get('wall_doors_condition')
        db.session.commit()
        flash('Exchange updated successfully!')
        return redirect(url_for('index'))
    return render_template('form.html', general=exchange)

@app.route('/export')
@login_required
def export():
    exchanges = GeneralInformation.query.all()
    data = []
    for exchange in exchanges:
        # Aggregate tower data
        tower_types = [tower.tower_type_hight for tower in exchange.towers] if exchange.tower_available == 'Yes' else ['N/A']
        tower_types_str = "; ".join(tower_types) if tower_types else 'N/A'
        # Aggregate DG data
        dg_details = []
        for dg in exchange.dgs:
            dg_info = f"DG: {dg.installed_dg}, Engine Make: {dg.engine_make}, Year: {dg.installation_year}, Status: {dg.dg_status}"
            dg_details.append(dg_info)
        dg_details_str = "; ".join(dg_details) if dg_details else 'N/A'
        # Aggregate Battery Bank data
        battery_details = []
        for battery in exchange.battery_banks:
            battery_info = f"Make: {battery.make_of_battery}, Capacity: {battery.battery_capacity}, Type: {battery.battery_type}"
            battery_details.append(battery_info)
        battery_details_str = "; ".join(battery_details) if battery_details else 'N/A'
        # Aggregate AC Unit data
        ac_details = []
        for ac in exchange.ac_units:
            ac_info = f"Location: {ac.location_of_ac_unit}, Make: {ac.ac_make}, Capacity: {ac.capacity_tons}"
            ac_details.append(ac_info)
        ac_details_str = "; ".join(ac_details) if ac_details else 'N/A'
        # Aggregate Fire Extinguisher data
        fe_details = []
        for fe in exchange.fire_extinguishers:
            fe_info = f"Installed: {fe.fe_installed}, No: {fe.no_of_fes}, Gas: {fe.type_of_gas}"
            fe_details.append(fe_info)
        fe_details_str = "; ".join(fe_details) if fe_details else 'N/A'
        data.append({
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
            'Tower Available': exchange.tower_available,
            'Tower Type/Height': tower_types_str,
            'Wapda Ref Number': exchange.power_info.wapda_ref_number if exchange.power_info else None,
            'Transformer Capacity': exchange.power_info.transformer_capacity if exchange.power_info else None,
            'Transformer Earthing': exchange.power_info.transformer_earthing if exchange.power_info else None,
            'DG Details': dg_details_str,
            'Make of Rectifier': exchange.power_info.make_of_rectifier if exchange.power_info else None,
            'Working Status (Power)': exchange.power_info.working_status if exchange.power_info else None,
            'Rectifier Capacity': exchange.power_info.rectifier_capacity if exchange.power_info else None,
            'No. of Modules': exchange.power_info.no_of_modules if exchange.power_info else None,
            'Capacity of Each Module': exchange.power_info.capacity_of_each_module if exchange.power_info else None,
            'Working Modules': exchange.power_info.working_modules if exchange.power_info else None,
            'Faulty Modules': exchange.power_info.faulty_modules if exchange.power_info else None,
            'Space for New Modules': exchange.power_info.space_for_new_modules if exchange.power_info else None,
            'Name of NEs Connected': exchange.power_info.name_of_nes_connected if exchange.power_info else None,
            'Load of Individual NE': exchange.power_info.load_of_individual_ne if exchange.power_info else None,
            'Grounding of Rectifier': exchange.power_info.grounding_of_rectifier if exchange.power_info else None,
            'SPD in Rectifier': exchange.power_info.spd_in_rectifier if exchange.power_info else None,
            'SPD Model': exchange.power_info.spd_model if exchange.power_info else None,
            'Total Installed SPDs': exchange.power_info.total_installed_spds if exchange.power_info else None,
            'No of Faulty SPDs': exchange.power_info.no_of_faulty_spds if exchange.power_info else None,
            'Battery Bank Details': battery_details_str,
            'AC Unit Details': ac_details_str,
            'Total Solar Size': exchange.solar_info.total_solar_size if exchange.solar_info else None,
            'PV Solar Panel Capacity': exchange.solar_info.pv_solar_panel_capacity if exchange.solar_info else None,
            'No. of PV Panels Installed': exchange.solar_info.no_of_pv_panels_installed if exchange.solar_info else None,
            'Make of PV Panels': exchange.solar_info.make_of_pv_panels if exchange.solar_info else None,
            'Charge Controller Make': exchange.solar_info.charge_controller_make if exchange.solar_info else None,
            'No. of Charge Controllers': exchange.solar_info.no_of_charge_controllers if exchange.solar_info else None,
            'Charge Controller Capacity': exchange.solar_info.charge_controller_capacity if exchange.solar_info else None,
            'Inverter Make': exchange.solar_info.inverter_make if exchange.solar_info else None,
            'Inverter Capacity': exchange.solar_info.inverter_capacity if exchange.solar_info else None,
            'No. of Inverters': exchange.solar_info.no_of_inverters if exchange.solar_info else None,
            'On Grid/Hybrid': exchange.solar_info.on_grid_hybrid if exchange.solar_info else None,
            'Roof Top/Ground': exchange.solar_info.roof_top_ground if exchange.solar_info else None,
            'Earthing Value': exchange.earthing.earthing_value if exchange.earthing else None,
            'No. of Pits': exchange.earthing.no_of_pits if exchange.earthing else None,
            'Fire Extinguisher Details': fe_details_str,
            'PMR Performed': exchange.pmr_info.pmr_performed if exchange.pmr_info else None,
            'Last Performed Date': exchange.pmr_info.last_performed_date if exchange.pmr_info else None,
            'AC Main Failure': exchange.alarm_extension.ac_main_failure if exchange.alarm_extension else None,
            'DC Low Voltages': exchange.alarm_extension.dc_low_voltages if exchange.alarm_extension else None,
            'Rectifier Failure': exchange.alarm_extension.rectifier_failure if exchange.alarm_extension else None,
            'Colocation': exchange.colocation_info.colocation if exchange.colocation_info else None,
            'Name of Colocation Vendors': exchange.colocation_info.name_of_colocation_vendors if exchange.colocation_info else None,
            'Load of Each Vendor': exchange.colocation_info.load_of_each_vendor if exchange.colocation_info else None,
            'Total Load': exchange.colocation_info.total_load if exchange.colocation_info else None,
            'Building Status': exchange.building_info.building_status if exchange.building_info else None,
            'Wall, Doors Condition': exchange.building_info.wall_doors_condition if exchange.building_info else None
        })
    df = pd.DataFrame(data)
    output = io.BytesIO()
    df.to_csv(output, index=False)
    output.seek(0)
    return send_file(
        output,
        mimetype='text/csv',
        as_attachment=True,
        download_name='exchanges.csv'
    )

@app.route('/view_exchanges')
@login_required
def view_exchanges():
    exchanges = GeneralInformation.query.all()
    return render_template('view_exchanges.html', exchanges=exchanges)

# Simplified for Railway; gunicorn will handle the server startup
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)  # For local development only