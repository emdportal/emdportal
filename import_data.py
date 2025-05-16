from app import db, GeneralInformation, PowerInformation, BatteryBankInformation, ACUnitsInformation, InstalledSolarInformation, Earthing, FireExtinguishers, PMRInformation, AlarmExtension, ColocationInformation, BuildingInformation
import pandas as pd

try:
    df = pd.read_excel("C:/Users/Admin/Desktop/Exchanges Master Database RTR.xlsx")
    for _, row in df.iterrows():
        general = GeneralInformation(
            sn=row['SN'],
            region=row['Region'],
            domain=row['Domain'],
            exchange_name=row['Exchange Name'],
            exchange_lic=row['Exchange LIC'],
            flc=row['FLC'],
            site_category=row['Site Category'],
            nes_installed=row['NEs Installed (Complete Detail)'],
            latitude=row['Latitude'],
            longitude=row['Longitude'],
            tower_available=row['Tower Available (Y/N)'] == 'Y',
            tower_type_height=row['Type and Hight of Tower']
        )
        db.session.add(general)
        db.session.commit()

        power = PowerInformation(
            sn=general.sn,
            wapda_ref_number=row['Wapda Ref Number'],
            transformer_capacity=row['Transformer Capacity'],
            transformer_earthing=row['Transformer Earthing'],
            installed_dgs=row['Installed DGs'],
            engine_make=row['Engine Make'],
            installation_year=row['Installation Year'] if pd.notna(row['Installation Year']) else None,
            dg_status=row['DG Status'],
            dg_starting_battery=row['DG Starting Battery'],
            smart_switch_installed=row['Smart Switch Installed (Y/N)'] == 'Y',
            ats_installed=row['ATS Installed (Y/N)'] == 'Y',
            ats_capacity=row['ATS Capacity'],
            faulty_ats_parts=row['Name of Faulty ATS Parts (SS,Relays,Contactor etc)'],
            no_faulty_ats_parts=row['No of Faulty ATS Parts'] if pd.notna(row['No of Faulty ATS Parts']) else None,
            load_on_dg_p1=row['Load on DG P1'] if pd.notna(row['Load on DG P1']) else None,
            load_on_dg_p2=row['Load on DG P2'] if pd.notna(row['Load on DG P2']) else None,
            load_on_dg_p3=row['Load on DG P3'] if pd.notna(row['Load on DG P3']) else None,
            site_load_total=row['Site Load Total'] if pd.notna(row['Site Load Total']) else None,
            site_load_p1=row['Site Load P1'] if pd.notna(row['Site Load P1']) else None,
            site_load_p2=row['Site Load P2'] if pd.notna(row['Site Load P2']) else None,
            site_load_p3=row['Site Load P3'] if pd.notna(row['Site Load P3']) else None
        )
        db.session.add(power)

        battery = BatteryBankInformation(
            sn=general.sn,
            make_of_battery=row['Make of Battery'],
            battery_capacity_ah=row['Battery Capacity (AH)'] if pd.notna(row['Battery Capacity (AH)']) else None,
            battery_type=row['Battery Type (2V/12V)'],
            no_of_cells_bank=row['No. of Cells/Bank'] if pd.notna(row['No. of Cells/Bank']) else None,
            date_of_installation=row['Date of Installation'],
            load_on_battery_bank=row['Load on Battery Bank (A)'] if pd.notna(row['Load on Battery Bank (A)']) else None,
            practical_backup_time=row['Practical Backup Time (Hrs)'] if pd.notna(row['Practical Backup Time (Hrs)']) else None,
            battery_installed_new_or_used=row['Battery Installed New or Used'],
            battery_moved_from=row['Battery Moved From (Incase Used Installed)']
        )
        db.session.add(battery)

        ac = ACUnitsInformation(
            sn=general.sn,
            location_of_ac_unit=row['Location of AC Unit'],
            working_status=row['Working Status (Y/N)'] == 'Y',
            ac_make=row['AC Make'],
            capacity_tons=row['Capacity (Tons)'] if pd.notna(row['Capacity (Tons)']) else None,
            type_of_ac=row['Type of AC'],
            mount_type=row['Mount Type'],
            date_of_installation=row['Date of Installation'],
            sequence_controller_installed=row['Sequence Controller Installed (Y/N)'] == 'Y',
            ac_load=row['AC Load'] if pd.notna(row['AC Load']) else None,
            total_ac_load=row['Total AC Load'] if pd.notna(row['Total AC Load']) else None,
            fault_nature_of_ac_unit=row['Fault Nature of AC Unit'],
            estimate_to_repair_ac=row['Estimate to Repair AC']
        )
        db.session.add(ac)

        solar = InstalledSolarInformation(
            sn=general.sn,
            total_solar_size_kw=row['Total Solar Size (KW)'] if pd.notna(row['Total Solar Size (KW)']) else None,
            pv_solar_panel_capacity_w=row['PV Solar Panel Capacity (W)'] if pd.notna(row['PV Solar Panel Capacity (W)']) else None,
            no_of_pv_panels_installed=row['No. of PV Panels Installed'] if pd.notna(row['No. of PV Panels Installed']) else None,
            make_of_pv_panels=row['Make of PV Panels'],
            charge_controller_make=row['Charge Controller Make'],
            no_of_charge_controllers=row['No. of Charge Controllers'] if pd.notna(row['No. of Charge Controllers']) else None,
            charge_controller_capacity=row['Charge Controller Capacity (A)'] if pd.notna(row['Charge Controller Capacity (A)']) else None,
            inverter_make=row['Inverter Make'],
            inverter_capacity_kw=row['Inverter Capacity (KW)'] if pd.notna(row['Inverter Capacity (KW)']) else None,
            no_of_inverters=row['No. of Inverters'] if pd.notna(row['No. of Inverters']) else None,
            on_grid_hybrid=row['On Grid/Hybrid?'],
            roof_top_ground=row['Roof Top/Ground?']
        )
        db.session.add(solar)

        earthing = Earthing(
            sn=general.sn,
            earthing_value=row['Earthing Value'],
            no_of_pits=row['No. of Pits'] if pd.notna(row['No. of Pits']) else None
        )
        db.session.add(earthing)

        fire = FireExtinguishers(
            sn=general.sn,
            fe_installed=row['FE Installed'] == 'Y',
            no_of_fes=row['No. of FEs'] if pd.notna(row['No. of FEs']) else None,
            type_of_gas=row['Type of Gas'],
            date_of_expiry=row['Date of Expiry']
        )
        db.session.add(fire)

        pmr = PMRInformation(
            sn=general.sn,
            pmr_performed=row['PMR Performed (Y/N)'] == 'Y',
            last_performed_date=row['Last Performed Date']
        )
        db.session.add(pmr)

        alarm = AlarmExtension(
            sn=general.sn,
            ac_main_failure=row['AC Main Failure (Y/N)'] == 'Y',
            dc_low_voltages=row['DC Low Voltages(Y/N)'] == 'Y',
            rectifier_failure=row['Rectifier Failure (Y/N)'] == 'Y'
        )
        db.session.add(alarm)

        colocation = ColocationInformation(
            sn=general.sn,
            colocation=row['Colocation(Y/N)'] == 'Y',
            name_of_colocation_vendors=row['Name of Colocation Vendors'],
            load_of_each_vendor=row['Load of Each Vendor'],
            total_load=row['Total Load'] if pd.notna(row['Total Load']) else None
        )
        db.session.add(colocation)

        building = BuildingInformation(
            sn=general.sn,
            building_status=row['Building Status(Good/Poor/Worst)'],
            wall_doors_condition=row['Wall,Doors Condition']
        )
        db.session.add(building)

        db.session.commit()
except Exception as e:
    db.session.rollback()
    print(f"Error importing data: {str(e)}")
print("Data imported successfully")