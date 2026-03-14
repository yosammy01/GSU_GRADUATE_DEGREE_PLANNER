import os
import socket
from flask import Flask, jsonify, render_template, request, redirect, url_for
import mysql.connector

app = Flask(__name__)

# This helps us see which "parallel" server is answering the request
container_id = socket.gethostname()

def get_db_connection():
    return mysql.connector.connect(
        # ------------------------------
        # PRODUCTION SETTINGS (UNCOMMENT FOR DEPLOYMENT)
        # host='db', # This matches the service name in your docker-compose.yml
        # port=3306,
        # user='flask_user',
        # password='your_secure_password',

        # ------------------------------
        # LOCAL DEVELOPMENT SETTINGS (UNCOMMENT FOR LOCAL TESTING)
        host='localhost',
        port=3306,
        user='root',  
        password='root',
        # ------------------------------

        database='gsu_catalog'
    )

def check_db_status():
    """Helper function to check database connection and return status dictionary."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()  
        cursor.execute("SELECT DATABASE();")
        db_name = cursor.fetchone()
        cursor.close()
        conn.close()
        return {"status": "Success", "database": db_name[0] if db_name else "N/A"}
    except Exception as e:
        return {"status": "Error", "message": str(e)}

def get_plans_from_db():
    """Fetches a list of all plan_ids from the Plan table."""
    plans = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT plan_id FROM Plan ORDER BY plan_id ASC;")
        # The result is a list of tuples, so we extract the first element of each tuple
        plans = [item[0] for item in cursor.fetchall()]
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error fetching plans from DB: {e}") # Log error to console
    return plans

def get_programs_from_db():
    """Fetches a list of all (major, degree) pairs from the Program table."""
    programs = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT major, degree FROM Program ORDER BY major, degree ASC;")
        programs = cursor.fetchall() # This will be a list of tuples
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error fetching programs from DB: {e}")
    return programs

@app.route('/')
def hello():
    db_status = check_db_status()
    plan_list = get_plans_from_db()
    return render_template('index.html', status=db_status, server=container_id, plans=plan_list)

@app.route('/view-plan', methods=['POST'])
def view_plan():
    """Handles the form submission from the main page to view a plan."""
    plan_id = request.form.get('plan_id')
    # In the future, you would fetch plan details from the DB and render a template.
    # For now, we'll just display the ID.
    return f"<h1>Viewing details for Plan: {plan_id}</h1><p><a href='/'>Back to Home</a></p>"

@app.route('/create-plan', methods=['GET', 'POST'])
def create_plan():
    """Handles the creation of a new plan."""
    if request.method == 'POST':
        # --- Handle Form Submission ---
        original_plan_id = request.form.get('plan_id')
        program_data = request.form.get('program', '').split('|')
        major = program_data[0] if len(program_data) > 0 else 'N/A'
        degree = program_data[1] if len(program_data) > 1 else 'N/A'
        
        final_plan_id = original_plan_id

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Check if the original plan_id exists
            cursor.execute("SELECT 1 FROM Plan WHERE plan_id = %s", (original_plan_id,))
            if cursor.fetchone():
                # If it exists, find an incremental name
                counter = 1
                while True:
                    new_plan_id = f"{original_plan_id}_{counter}"
                    cursor.execute("SELECT 1 FROM Plan WHERE plan_id = %s", (new_plan_id,))
                    if not cursor.fetchone():
                        final_plan_id = new_plan_id
                        break
                    counter += 1

            cursor.execute("INSERT INTO Plan (plan_id) VALUES (%s)", (final_plan_id,))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error creating plan: {e}")
            
        return redirect(url_for('edit_plan', plan_id=final_plan_id, major=major, degree=degree))

    # --- Display Form (GET Request) ---
    programs = get_programs_from_db()
    return render_template('create_plan.html', programs=programs)

@app.route('/edit-plan/<plan_id>')
def edit_plan(plan_id):
    """Displays requirements and allows adding classes to the plan."""
    major = request.args.get('major')
    degree = request.args.get('degree')
    selected_req = request.args.get('requirement')

    requirements = []
    classes = []
    plan_classes = []
    chosen_exclusive_option = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Fetch requirements for this program
        cursor.execute("SELECT requirement_name FROM Program_Has_Requirements WHERE major = %s AND degree = %s", (major, degree))
        requirements = [row[0] for row in cursor.fetchall()]

        # 2. Fetch classes for the selected requirement
        if selected_req:
            specific_classes = []
            range_classes = []
            
            try:
                # Fetch specific classes using LEFT JOINs to guarantee they always appear
                cursor.execute("""
                    SELECT rc.class_prefix, rc.graduate_range AS class_number, cc.class_title, COALESCE(cc.credits, cg.credits) 
                    FROM Requirements_Composed_Of_Class_Groupings rc
                    LEFT JOIN Class_Groupings cg ON rc.class_prefix = cg.class_prefix AND rc.graduate_range = cg.graduate_range
                    LEFT JOIN Class_Catalog cc ON rc.class_prefix = cc.class_prefix AND rc.graduate_range = cc.graduate_class_number
                    WHERE rc.requirement_name = %s AND rc.graduate_range NOT LIKE '%%-%%'
                """, (selected_req,))
                specific_classes = cursor.fetchall()
            except Exception as e:
                print(f"Error fetching specific classes: {e}")

            try:
                # Fetch elective range classes safely
                cursor.execute("""
                    SELECT cc.class_prefix, cc.graduate_class_number AS class_number, cc.class_title, cc.credits
                    FROM Requirements_Composed_Of_Class_Groupings rc
                    JOIN Class_Catalog cc ON rc.class_prefix = cc.class_prefix
                    WHERE rc.requirement_name = %s AND rc.graduate_range LIKE '%%-%%'
                      AND cc.graduate_class_number >= SUBSTRING_INDEX(rc.graduate_range, '-', 1)
                      AND cc.graduate_class_number <= SUBSTRING_INDEX(rc.graduate_range, '-', -1)
                """, (selected_req,))
                range_classes = cursor.fetchall()
            except Exception as e:
                print(f"Error fetching range classes: {e}")
                
            classes = specific_classes + range_classes
            classes.sort(key=lambda x: (x[0], x[1]))

        # 3. Fetch currently added classes for this plan
        cursor.execute("""
            SELECT prc.class_prefix, prc.class_number, cc.class_title, COALESCE(cc.credits, cg.credits)
            FROM Plan_Requires_Class prc
            LEFT JOIN Class_Catalog cc ON prc.class_prefix = cc.class_prefix AND prc.class_number = cc.graduate_class_number
            LEFT JOIN Class_Groupings cg ON prc.class_prefix = cg.class_prefix AND prc.class_number = cg.graduate_range
            WHERE prc.plan_id = %s
        """, (plan_id,))
        plan_classes = cursor.fetchall()

        # 4. Check for exclusive option selection
        exclusive_options = {
            'Thesis Option': [('CSC', '8999')],
            'Project Option': [('CSC', '8930'), ('CSC', '8940')],
            'Course Only Option': [('CSC', '8901')]
        }
        plan_class_tuples = [(pc[0], pc[1]) for pc in plan_classes]

        for option, classes_in_option in exclusive_options.items():
            if any(cls in plan_class_tuples for cls in classes_in_option):
                chosen_exclusive_option = option
                break

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error fetching plan details: {e}")

    return render_template('edit_plan.html', plan_id=plan_id, major=major, degree=degree,
                           requirements=requirements, selected_req=selected_req,
                           classes=classes, plan_classes=plan_classes,
                           chosen_exclusive_option=chosen_exclusive_option)

@app.route('/add-class', methods=['POST'])
def add_class():
    """Adds a selected class to the plan."""
    plan_id = request.form.get('plan_id')
    major = request.form.get('major')
    degree = request.form.get('degree')
    requirement = request.form.get('requirement')
    
    class_data = request.form.get('class_data', '').split('|')
    class_prefix = class_data[0] if len(class_data) > 0 else ''
    class_number = class_data[1] if len(class_data) > 1 else ''

    if plan_id and class_prefix and class_number:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT IGNORE INTO Class (class_prefix, class_number) VALUES (%s, %s)", (class_prefix, class_number))
            cursor.execute("INSERT IGNORE INTO Plan_Requires_Class (plan_id, class_prefix, class_number) VALUES (%s, %s, %s)",
                           (plan_id, class_prefix, class_number))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error adding class: {e}")

    return redirect(url_for('edit_plan', plan_id=plan_id, major=major, degree=degree, requirement=requirement))

@app.route('/edit-program', methods=['GET'])
def edit_program():
    """Displays program requirements and allows editing class groupings."""
    program_data = request.args.get('program_data')
    if program_data:
        parts = program_data.split('|')
        major = parts[0]
        degree = parts[1] if len(parts) > 1 else ''
    else:
        major = request.args.get('major')
        degree = request.args.get('degree')
        
    selected_req = request.args.get('requirement')

    programs = get_programs_from_db()
    requirements = []
    classes = []
    all_classes = []

    if major and degree:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Fetch requirements for this program
            cursor.execute("SELECT requirement_name FROM Program_Has_Requirements WHERE major = %s AND degree = %s", (major, degree))
            requirements = [row[0] for row in cursor.fetchall()]

            # Fetch classes for the selected requirement
            if selected_req:
                cursor.execute("""
                    SELECT rc.class_prefix, rc.graduate_range, cg.credits 
                    FROM Requirements_Composed_Of_Class_Groupings rc
                    LEFT JOIN Class_Groupings cg ON rc.class_prefix = cg.class_prefix AND rc.graduate_range = cg.graduate_range
                    WHERE rc.requirement_name = %s
                """, (selected_req,))
                classes = cursor.fetchall()
                
                # Fetch all available class groupings to provide a list to add from
                cursor.execute("SELECT class_prefix, graduate_range, credits FROM Class_Groupings")
                all_classes = cursor.fetchall()

            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error fetching program details: {e}")

    return render_template('edit_program.html', programs=programs, major=major, degree=degree,
                           requirements=requirements, selected_req=selected_req,
                           classes=classes, all_classes=all_classes)

@app.route('/add-grouping', methods=['POST'])
def add_grouping():
    major = request.form.get('major')
    degree = request.form.get('degree')
    requirement = request.form.get('requirement')
    
    class_data = request.form.get('class_data', '').split('|')
    class_prefix = class_data[0] if len(class_data) > 0 else ''
    graduate_range = class_data[1] if len(class_data) > 1 else ''

    if requirement and class_prefix and graduate_range:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT IGNORE INTO Requirements_Composed_Of_Class_Groupings (requirement_name, class_prefix, graduate_range) VALUES (%s, %s, %s)",
                           (requirement, class_prefix, graduate_range))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error adding grouping: {e}")

    return redirect(url_for('edit_program', major=major, degree=degree, requirement=requirement))

@app.route('/remove-grouping', methods=['POST'])
def remove_grouping():
    major = request.form.get('major')
    degree = request.form.get('degree')
    requirement = request.form.get('requirement')
    class_prefix = request.form.get('class_prefix')
    graduate_range = request.form.get('graduate_range')

    if requirement and class_prefix and graduate_range:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Requirements_Composed_Of_Class_Groupings WHERE requirement_name = %s AND class_prefix = %s AND graduate_range = %s",
                           (requirement, class_prefix, graduate_range))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error removing grouping: {e}")

    return redirect(url_for('edit_program', major=major, degree=degree, requirement=requirement))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)