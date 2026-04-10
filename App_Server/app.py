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
        # AKS SETTINGS (UNCOMMENT FOR AKS DEPLOYMENT)
        # host='db', # This matches the service name in your docker-compose.yml
        # port=3306,
        # user='root',
        # password='root',

        # ------------------------------
        # DOCKER SETTINGS (UNCOMMENT FOR DOCKER DEPLOYMENT)
        # host='db', # This matches the service name in your docker-compose.yml
        # port=3306,
        # user='flask_user',
        # password='your_secure_password',

        # ------------------------------
        # LOCAL DEVELOPMENT SETTINGS (UNCOMMENT FOR LOCAL TESTING)
        host='localhost',
        port=3307,
        user='root',  
        password='root',
        # ------------------------------

        database='gsu_catalog'
    )

def check_db_status():
    """Helper function to check database connection and return status dictionary."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()  
        cursor.execute("SELECT DATABASE();")
        db_name = cursor.fetchone()
        return {"status": "Success", "database": db_name[0] if db_name else "N/A"}
    except Exception as e:
        return {"status": "Error", "message": str(e)}
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

def get_plans_from_db():
    """Fetches a list of all plan_ids from the Plan table."""
    plans = []
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT plan_id FROM Plan ORDER BY plan_id ASC;")
        # The result is a list of tuples, so we extract the first element of each tuple
        plans = [item[0] for item in cursor.fetchall()]
    except Exception as e:
        print(f"Error fetching plans from DB: {e}") # Log error to console
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
    return plans

def get_programs_from_db():
    """Fetches a list of all (major, degree) pairs from the Program table."""
    programs = []
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT major, degree FROM Program ORDER BY major, degree ASC;")
        programs = cursor.fetchall() # This will be a list of tuples
    except Exception as e:
        print(f"Error fetching programs from DB: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
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
    student_id = request.form.get('student_id')
    student_name = request.form.get('student_name')

    if not plan_id:
        return redirect(url_for('hello'))
    if not student_id or not student_name:
        return "Student ID and Name are required to view a plan.", 400

    plan_details = {}
    classes_by_req = {}
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Verify the student matches the chosen plan
        cursor.execute("""
            SELECT s.id, s.name 
            FROM Student s
            JOIN Student_Plans_Plan spp ON s.id = spp.id
            WHERE spp.plan_id = %s
        """, (plan_id,))
        student_info = cursor.fetchone()
        
        if not student_info:
            return "No student associated with this plan.", 404
        if student_info['id'].lower() != student_id.lower() or student_info['name'].lower() != student_name.lower():
            return "The entered Student ID or Name does not match the chosen plan's student.", 403

        # 1. Fetch plan details (major, degree)
        cursor.execute("SELECT major, degree FROM Plan WHERE plan_id = %s", (plan_id,))
        plan_info = cursor.fetchone()
        
        if not plan_info:
            return "Plan not found", 404
        
        plan_details['plan_id'] = plan_id
        plan_details['major'] = plan_info['major']
        plan_details['degree'] = plan_info['degree']

        # 2. Fetch classes currently in this plan FIRST, to identify chosen exclusive options
        cursor.execute("""
            SELECT 
                prc.requirement_name, prc.class_prefix, prc.class_number, 
                cc.class_title, COALESCE(prc.credits, cc.credits) AS credits,
                prc.taken_planned, prc.semester, prc.year, prc.grade,
                0 AS is_placeholder
            FROM Plan_Requires_Class prc
            LEFT JOIN Class_Catalog cc ON prc.class_prefix = cc.class_prefix AND prc.class_number = cc.graduate_class_number
            WHERE prc.plan_id = %s
        """, (plan_id,))
        
        plan_classes_rows = cursor.fetchall()
        plan_class_ids = {(c['class_prefix'], c['class_number']) for c in plan_classes_rows}

        exclusive_options = {
            'Thesis Option': [('CSC', '8999')],
            'Project Option': [('CSC', '8930'), ('CSC', '8940')],
            'Course Only Option': [('CSC', '8901')]
        }
        chosen_exclusive_option = None
        for option, classes_in_option in exclusive_options.items():
            if any(cls in plan_class_ids for cls in classes_in_option):
                chosen_exclusive_option = option
                break
        exclusive_reqs = set(exclusive_options.keys())

        # 3. Fetch all requirements for the program. Calculate total credits.
        cursor.execute("""
            SELECT
                phr.requirement_name,
                SUM(cg.credits) AS total_credits_required
            FROM Program_Has_Requirements phr
            LEFT JOIN Requirements_Composed_Of_Class_Groupings rcog ON phr.requirement_name = rcog.requirement_name
            LEFT JOIN Class_Groupings cg ON rcog.grouping_id = cg.grouping_id
            WHERE phr.major = %s AND phr.degree = %s
            GROUP BY phr.requirement_name
        """, (plan_info['major'], plan_info['degree']))

        requirements_info = {}
        for row in cursor.fetchall():
            req_name = row['requirement_name']
            
            # Skip unchosen exclusive options
            if req_name in exclusive_reqs and chosen_exclusive_option and req_name != chosen_exclusive_option:
                continue
                
            classes_by_req[req_name] = []
            requirements_info[req_name] = {
                'total_credits': row['total_credits_required'],
                'planned_credits': 0
            }

        # Fetch groupings to identify missing ones
        cursor.execute("""
            SELECT rcog.requirement_name, cg.grouping_id, cg.credits, cg.grouping_name
            FROM Program_Has_Requirements phr
            JOIN Requirements_Composed_Of_Class_Groupings rcog ON phr.requirement_name = rcog.requirement_name
            JOIN Class_Groupings cg ON rcog.grouping_id = cg.grouping_id
            WHERE phr.major = %s AND phr.degree = %s
        """, (plan_info['major'], plan_info['degree']))
        
        all_groupings_by_req = {}
        for row in cursor.fetchall():
            req_name = row['requirement_name']
            if req_name not in requirements_info:
                continue # Skipped exclusive option
            if req_name not in all_groupings_by_req:
                all_groupings_by_req[req_name] = []
            all_groupings_by_req[req_name].append(row)

        cursor.execute("SELECT grouping_id, class_prefix, min_class_number, max_class_number FROM Class_Grouping_Elements")
        elements_by_grouping = {}
        for row in cursor.fetchall():
            g_id = row['grouping_id']
            if g_id not in elements_by_grouping:
                elements_by_grouping[g_id] = []
            elements_by_grouping[g_id].append(row)

        grade_points = {
            'A+': 4.3, 'A': 4.0, 'A-': 3.7,
            'B+': 3.3, 'B': 3.0, 'B-': 2.7,
            'C+': 2.3, 'C': 2.0, 'C-': 1.7,
            'D': 1.0, 'F': 0.0
        }
        current_qp = 0.0
        current_gpa_credits = 0.0
        possible_qp = 0.0
        possible_gpa_credits = 0.0

        # 4. Group planned classes by requirement and sum their credits
        for c in plan_classes_rows:
            req_name = c['requirement_name']
            if req_name not in classes_by_req:
                classes_by_req[req_name] = []
            classes_by_req[req_name].append(c)
            if c['credits'] and req_name in requirements_info:
                requirements_info[req_name]['planned_credits'] += c['credits']

            grade = c.get('grade')
            credits = c.get('credits')
            if grade and isinstance(grade, str) and grade.strip().upper() in grade_points and credits:
                pts = grade_points[grade.strip().upper()] * float(credits)
                if c.get('taken_planned') == 1:
                    current_qp += pts
                    current_gpa_credits += float(credits)
                possible_qp += pts
                possible_gpa_credits += float(credits)

        plan_details['current_gpa'] = f"{current_qp / current_gpa_credits:.2f}" if current_gpa_credits > 0 else 'N/A'
        plan_details['possible_gpa'] = f"{possible_qp / possible_gpa_credits:.2f}" if possible_gpa_credits > 0 else 'N/A'

        # 5. Evaluate satisfied/unsatisfied groupings and add placeholder for remainder
        for req_name, groupings in all_groupings_by_req.items():
            unsatisfied_groupings = []
            
            for g in groupings:
                g_id = g['grouping_id']
                g_req_credits = g['credits']
                elements = elements_by_grouping.get(g_id, [])
                
                is_satisfied = False
                if g_req_credits is None:
                    for el in elements:
                        for pc_prefix, pc_number in plan_class_ids:
                            if pc_prefix == el['class_prefix'] and pc_number.isdigit() and int(el['min_class_number']) <= int(pc_number) <= int(el['max_class_number']):
                                is_satisfied = True
                                break
                        if is_satisfied:
                            break
                elif g_req_credits > 0:
                    planned_credits = 0
                    for pc in plan_classes_rows:
                        if pc['requirement_name'] == req_name and pc['credits']:
                            for el in elements:
                                if pc['class_prefix'] == el['class_prefix'] and pc['class_number'].isdigit() and int(el['min_class_number']) <= int(pc['class_number']) <= int(el['max_class_number']):
                                    planned_credits += pc['credits']
                                    break
                    if planned_credits >= g_req_credits:
                        is_satisfied = True
                else: # e.g. 0 credits
                    for el in elements:
                        for pc_prefix, pc_number in plan_class_ids:
                            if pc_prefix == el['class_prefix'] and pc_number.isdigit() and int(el['min_class_number']) <= int(pc_number) <= int(el['max_class_number']):
                                is_satisfied = True
                                break
                        if is_satisfied:
                            break

                if not is_satisfied:
                    unsatisfied_groupings.append(g)

            if unsatisfied_groupings:
                missing_names = [g['grouping_name'] for g in unsatisfied_groupings if g['grouping_name']]
                missing_names_str = ", ".join(missing_names)
                
                req_info = requirements_info.get(req_name, {})
                total = req_info.get('total_credits') or 0
                remaining_credits = total - req_info.get('planned_credits', 0)
                
                if remaining_credits > 0:
                    title = f'{remaining_credits} credits remaining to be planned'
                    if missing_names_str:
                        title += f' (Missing: {missing_names_str})'
                else:
                    title = f'Remaining to be planned: {missing_names_str}'
                    remaining_credits = 0
                
                classes_by_req[req_name].append({
                    'requirement_name': req_name, 'class_prefix': 'TBD', 'class_number': '',
                    'class_title': title,
                    'credits': remaining_credits, 'semester': 'Needed', 'year': None, 'grade': None,
                    'taken_planned': 0, 'is_placeholder': 1
                })

    except Exception as e:
        print(f"Error fetching plan view details: {e}")
        return "Error loading plan", 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
            
    return render_template('view_plan.html', plan=plan_details, classes_by_req=classes_by_req)

@app.route('/delete-plan', methods=['POST'])
def delete_plan():
    """Deletes a selected plan from the database."""
    plan_id = request.form.get('plan_id')
    student_id = request.form.get('student_id')
    student_name = request.form.get('student_name')

    if plan_id and student_id and student_name:
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT s.id, s.name 
                FROM Student s
                JOIN Student_Plans_Plan spp ON s.id = spp.id
                WHERE spp.plan_id = %s
            """, (plan_id,))
            student_info = cursor.fetchone()
            
            if not student_info or student_info[0].lower() != student_id.lower() or student_info[1].lower() != student_name.lower():
                return "The entered Student ID or Name does not match the chosen plan's student. Deletion denied.", 403

            cursor.execute("DELETE FROM Plan WHERE plan_id = %s", (plan_id,))
            conn.commit()
        except Exception as e:
            print(f"Error deleting plan: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            
    return redirect(url_for('hello'))

@app.route('/create-plan', methods=['GET', 'POST'])
def create_plan():
    """Handles the creation of a new plan."""
    if request.method == 'POST':
        # --- Handle Form Submission ---
        original_plan_id = request.form.get('plan_id')
        program_data = request.form.get('program', '').split('|')
        major = program_data[0] if len(program_data) > 0 else None
        degree = program_data[1] if len(program_data) > 1 else None
        
        student_id = request.form.get('student_id')
        student_name = request.form.get('student_name')

        if not original_plan_id or not major or not degree or not student_id or not student_name:
            return "Plan ID, a valid Program selection, Student ID, and Student Name are required. Please go back and try again.", 400

        final_plan_id = original_plan_id

        conn = None
        cursor = None
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

            # Insert student details into the Student table
            cursor.execute("INSERT IGNORE INTO Student (id, name) VALUES (%s, %s)", (student_id, student_name))

            cursor.execute("INSERT INTO Plan (plan_id, major, degree) VALUES (%s, %s, %s)", (final_plan_id, major, degree))
            
            # Link the student to the created plan
            cursor.execute("INSERT INTO Student_Plans_Plan (id, plan_id) VALUES (%s, %s)", (student_id, final_plan_id))
            conn.commit()
        except Exception as e:
            print(f"Error creating plan: {e}")
            return "An error occurred while creating the plan. Please ensure all fields are filled correctly and try again.", 500
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
                
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

    student_id = ""
    student_name = ""

    # If major/degree are missing, the plan may not have a program assigned yet.
    if not major or not degree:
        db_major, db_degree = None, None
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT major, degree FROM Plan WHERE plan_id = %s", (plan_id,))
            result = cursor.fetchone()
            if result:
                db_major, db_degree = result[0], result[1]
                
            cursor.execute("""
                SELECT s.id, s.name 
                FROM Student s
                JOIN Student_Plans_Plan spp ON s.id = spp.id
                WHERE spp.plan_id = %s
            """, (plan_id,))
            student_info = cursor.fetchone()
            if student_info:
                student_id, student_name = student_info[0], student_info[1]
        except Exception as e:
            print(f"Error checking plan program: {e}")
            return "Error loading plan.", 500
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
                
        # If program exists in DB but not URL, redirect to the full URL
        if db_major and db_degree:
            return redirect(url_for('edit_plan', plan_id=plan_id, major=db_major, degree=db_degree))
        
        # If program is not in DB, show assignment form
        else:
            programs = get_programs_from_db()
            return render_template('edit_plan.html', plan_id=plan_id, major=None, degree=None,
                                   programs=programs, needs_program_assignment=True,
                                   student_id=student_id, student_name=student_name)

    requirements = []
    classes = []
    plan_classes = []
    chosen_exclusive_option = None
    plan_classes_grouped = {}

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT s.id, s.name 
            FROM Student s
            JOIN Student_Plans_Plan spp ON s.id = spp.id
            WHERE spp.plan_id = %s
        """, (plan_id,))
        student_info = cursor.fetchone()
        if student_info:
            student_id, student_name = student_info[0], student_info[1]
        
        # 1. Fetch requirements for this program
        cursor.execute("SELECT requirement_name FROM Program_Has_Requirements WHERE major = %s AND degree = %s", (major, degree))
        requirements = [row[0] for row in cursor.fetchall()]

        # Fetch currently added classes for this plan FIRST, as it's needed to determine which requirements are satisfied
        cursor.execute("""
            SELECT prc.class_prefix, prc.class_number, cc.class_title, COALESCE(prc.credits, cc.credits) as credits, prc.requirement_name,
                   prc.taken_planned, prc.semester, prc.year, prc.grade, 0 AS is_placeholder
            FROM Plan_Requires_Class prc
            LEFT JOIN Class_Catalog cc ON prc.class_prefix = cc.class_prefix AND prc.class_number = cc.graduate_class_number
            WHERE prc.plan_id = %s
            ORDER BY prc.requirement_name, prc.class_prefix, prc.class_number
        """, (plan_id,))
        plan_classes = cursor.fetchall()
        plan_class_ids = {(pc[0], pc[1]) for pc in plan_classes}

        # 1a. Calculate total credits required for each requirement
        requirements_info = {}
        cursor.execute("""
            SELECT
                phr.requirement_name,
                SUM(cg.credits)
            FROM Program_Has_Requirements phr
            LEFT JOIN Requirements_Composed_Of_Class_Groupings rcog ON phr.requirement_name = rcog.requirement_name
            LEFT JOIN Class_Groupings cg ON rcog.grouping_id = cg.grouping_id
            WHERE phr.major = %s AND phr.degree = %s
            GROUP BY phr.requirement_name
        """, (major, degree))

        for row in cursor.fetchall():
            req_name = row[0]
            total_credits = row[1]
            requirements_info[req_name] = {
                'total_credits': total_credits,
                'planned_credits': 0
            }

        # 2. Fetch classes for the selected requirement
        if selected_req:
            # 1. Get all groupings for the requirement, distinguishing between
            #    'pick one' (credits is NULL/0) and 'accumulate credits' (credits > 0)
            cursor.execute("""
                SELECT cg.grouping_id, cg.credits
                FROM Requirements_Composed_Of_Class_Groupings rcog
                JOIN Class_Groupings cg ON rcog.grouping_id = cg.grouping_id
                WHERE rcog.requirement_name = %s
            """, (selected_req,))
            all_groupings_for_req = cursor.fetchall()

            satisfied_credit_groupings = set()
            satisfied_pick_one_groupings = set()
            
            # 2. Identify all satisfied groupings (both credit-based and "pick one")
            for g_id, g_req_credits in all_groupings_for_req:
                # Find all classes that could belong to this grouping
                cursor.execute("""
                    SELECT class_prefix, min_class_number, max_class_number
                    FROM Class_Grouping_Elements WHERE grouping_id = %s
                """, (g_id,))
                elements = cursor.fetchall()

                # Case A: "Pick One" grouping (where credits is NULL or 0 in the DB)
                if g_req_credits is None or g_req_credits == 0:
                    for el_prefix, el_min, el_max in elements:
                        for pc_prefix, pc_number in plan_class_ids:
                            if pc_prefix == el_prefix and pc_number.isdigit() and int(el_min) <= int(pc_number) <= int(el_max):
                                satisfied_pick_one_groupings.add(g_id)
                                break
                        if g_id in satisfied_pick_one_groupings:
                            break

                # Case B: Credit-accumulation grouping
                elif g_req_credits > 0:
                    planned_credits = 0
                    for pc in plan_classes:
                        pc_prefix, pc_number, _, pc_credits, pc_req_name, *_ = pc
                        if pc_req_name == selected_req and pc_credits:
                            for el_prefix, el_min, el_max in elements:
                                if pc_prefix == el_prefix and pc_number.isdigit() and int(el_min) <= int(pc_number) <= int(el_max):
                                    planned_credits += pc_credits
                                    break # Class matched, move to next planned class
                    if planned_credits >= g_req_credits:
                        satisfied_credit_groupings.add(g_id)

            # 3. Fetch all possible classes for the UNSATISFIED groupings
            available_classes = []
            
            for g_id, g_req_credits in all_groupings_for_req:
                # If a grouping is satisfied (either type), skip it
                if g_id in satisfied_credit_groupings or g_id in satisfied_pick_one_groupings:
                    continue

                # Fetch all catalog classes for this grouping
                cursor.execute("""
                    SELECT
                        cc.class_prefix,
                        cc.graduate_class_number,
                        cc.class_title,
                        COALESCE(cc.credits, 0) AS credits
                    FROM Class_Grouping_Elements cge
                    JOIN Class_Catalog cc ON cge.class_prefix = cc.class_prefix
                        AND CAST(cc.graduate_class_number AS UNSIGNED) >= CAST(cge.min_class_number AS UNSIGNED)
                        AND CAST(cc.graduate_class_number AS UNSIGNED) <= CAST(cge.max_class_number AS UNSIGNED)
                    WHERE cge.grouping_id = %s
                """, (g_id,))
                
                for p_class in cursor.fetchall():
                    class_id = (p_class[0], p_class[1])
                    # Add if not already in the plan
                    if class_id not in plan_class_ids:
                        available_classes.append(p_class)

            # 4. Deduplicate and sort
            classes = []
            seen_classes = set()
            for ac in available_classes:
                class_id = (ac[0], ac[1])
                if class_id not in seen_classes:
                    classes.append(ac)
                    seen_classes.add(class_id)
            
            classes.sort(key=lambda x: (x[0], x[1]))

        # 4. Check for exclusive option selection
        exclusive_options = {
            'Thesis Option': [('CSC', '8999')],
            'Project Option': [('CSC', '8930'), ('CSC', '8940')],
            'Course Only Option': [('CSC', '8901')]
        }

        for option, classes_in_option in exclusive_options.items():
            if any(cls in plan_class_ids for cls in classes_in_option):
                chosen_exclusive_option = option
                break

        # 5. Group classes by requirement, calculating planned credits and adding placeholders
        for req_name in requirements:
            plan_classes_grouped[req_name] = []

        for pc in plan_classes:
            req_name = pc[4]
            credits = pc[3]
            if req_name in plan_classes_grouped:
                plan_classes_grouped[req_name].append(pc)
                if credits and requirements_info.get(req_name):
                    requirements_info[req_name]['planned_credits'] += credits
        
        for req_name, req_info in requirements_info.items():
            total = req_info.get('total_credits') or 0
            if total > 0:
                remaining_credits = total - req_info['planned_credits']
                if remaining_credits > 0:
                    # (prefix, number, title, credits, req_name, taken_planned, semester, year, grade, is_placeholder)
                    placeholder = ('TBD', '', f'{remaining_credits} credits remaining to be planned',
                                   remaining_credits, req_name, 0, 'Needed', None, None, 1)
                    if req_name in plan_classes_grouped:
                        plan_classes_grouped[req_name].append(placeholder)

    except Exception as e:
        print(f"Error fetching plan details: {e}")
        return "An error occurred while loading the plan editor.", 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
            
    return render_template('edit_plan.html', plan_id=plan_id, major=major, degree=degree,
                           requirements=requirements, selected_req=selected_req,
                           classes=classes, plan_classes=plan_classes_grouped,
                           chosen_exclusive_option=chosen_exclusive_option,
                           student_id=student_id, student_name=student_name)

@app.route('/assign-program', methods=['POST'])
def assign_program():
    """Assigns a program (major/degree) to a plan."""
    plan_id = request.form.get('plan_id')
    program_data = request.form.get('program', '').split('|')
    major = program_data[0] if len(program_data) > 0 else None
    degree = program_data[1] if len(program_data) > 1 else None

    if not all([plan_id, major, degree]):
        return "Invalid data submitted. Plan ID and Program are required.", 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE Plan SET major = %s, degree = %s WHERE plan_id = %s", (major, degree, plan_id))
        conn.commit()
    except Exception as e:
        print(f"Error assigning program to plan: {e}")
        return "Error updating plan.", 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

    return redirect(url_for('edit_plan', plan_id=plan_id, major=major, degree=degree))


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
    original_credits = class_data[2] if len(class_data) > 2 else '0'

    manual_credits = request.form.get('manual_credits')
    taken_planned = request.form.get('taken_planned')
    semester = request.form.get('semester')
    year = request.form.get('year')
    grade = request.form.get('grade')

    if plan_id and class_prefix and class_number and requirement:
        taken_planned_val = 1 if taken_planned == '1' else 0
        year_val = int(year) if year and year.isdigit() else None
        grade_val = grade if grade else None
        
        orig_credits_val = 0
        if original_credits and original_credits != 'None' and original_credits.isdigit():
            orig_credits_val = int(original_credits)

        credits_to_insert = None
        if manual_credits and manual_credits.isdigit() and orig_credits_val == 0:
            credits_to_insert = int(manual_credits)
        
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT IGNORE INTO Class (class_prefix, class_number) VALUES (%s, %s)", (class_prefix, class_number))
            cursor.execute("""INSERT IGNORE INTO Plan_Requires_Class (plan_id, class_prefix, class_number, requirement_name, taken_planned, semester, year, grade, credits) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                           (plan_id, class_prefix, class_number, requirement, taken_planned_val, semester, year_val, grade_val, credits_to_insert))
            conn.commit()
        except Exception as e:
            print(f"Error adding class: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

    return redirect(url_for('edit_plan', plan_id=plan_id, major=major, degree=degree, requirement=requirement))

@app.route('/remove-class', methods=['POST'])
def remove_class():
    """Removes a selected class from the plan."""
    plan_id = request.form.get('plan_id')
    major = request.form.get('major')
    degree = request.form.get('degree')
    requirement = request.form.get('requirement')
    class_prefix = request.form.get('class_prefix')
    class_number = request.form.get('class_number')

    if plan_id and class_prefix and class_number:
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Plan_Requires_Class WHERE plan_id = %s AND class_prefix = %s AND class_number = %s",
                           (plan_id, class_prefix, class_number))
            conn.commit()
        except Exception as e:
            print(f"Error removing class: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

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
    all_requirements = []
    all_catalog_classes = []

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT requirement_name FROM Requirements ORDER BY requirement_name ASC")
        all_requirements = [row[0] for row in cursor.fetchall()]
        
        # Fetch all available class groupings for global management and dropdowns
        cursor.execute("SELECT grouping_id, grouping_name, credits FROM Class_Groupings")
        all_classes = cursor.fetchall()
        
        # Fetch all catalog classes globally
        cursor.execute("SELECT class_prefix, graduate_class_number, credits, class_title FROM Class_Catalog ORDER BY class_prefix, graduate_class_number")
        all_catalog_classes = cursor.fetchall()

        if major and degree:
            # Fetch requirements for this program
            cursor.execute("SELECT requirement_name FROM Program_Has_Requirements WHERE major = %s AND degree = %s", (major, degree))
            requirements = [row[0] for row in cursor.fetchall()]

            # Fetch classes for the selected requirement
            if selected_req:
                cursor.execute("""
                    SELECT rc.grouping_id, cg.grouping_name, cg.credits
                    FROM Requirements_Composed_Of_Class_Groupings rc
                    LEFT JOIN Class_Groupings cg ON rc.grouping_id = cg.grouping_id
                    WHERE rc.requirement_name = %s                   
                """, (selected_req,))
                classes = cursor.fetchall()
                
    except Exception as e:
        print(f"Error fetching program details: {e}")        
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

    return render_template('edit_program.html', programs=programs, major=major, degree=degree,
                           requirements=requirements, selected_req=selected_req,                           
                           classes=classes, all_classes=all_classes, all_requirements=all_requirements,
                           all_catalog_classes=all_catalog_classes)

@app.route('/global-management', methods=['GET'])
def global_management():
    """Displays the page for managing global requirements, groupings, and catalog classes."""
    all_classes = []
    all_requirements = []
    all_catalog_classes = []

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT requirement_name FROM Requirements ORDER BY requirement_name ASC")
        all_requirements = [row[0] for row in cursor.fetchall()]
        
        cursor.execute("SELECT grouping_id, grouping_name, credits FROM Class_Groupings")
        all_classes = cursor.fetchall()
        
        cursor.execute("SELECT class_prefix, graduate_class_number, credits, class_title FROM Class_Catalog ORDER BY class_prefix, graduate_class_number")
        all_catalog_classes = cursor.fetchall()
    except Exception as e:
        print(f"Error fetching global details: {e}")        
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

    return render_template('global_management.html', all_classes=all_classes, all_requirements=all_requirements, all_catalog_classes=all_catalog_classes)

@app.route('/create-program', methods=['POST'])
def create_program():
    major = request.form.get('major')
    degree = request.form.get('degree')
    if major and degree:
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT IGNORE INTO Program (major, degree) VALUES (%s, %s)", (major, degree))
            conn.commit()
        except Exception as e:
            print(f"Error creating program: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
    return redirect(url_for('edit_program', major=major, degree=degree))

@app.route('/add-requirement-to-program', methods=['POST'])
def add_requirement_to_program():
    major = request.form.get('major')
    degree = request.form.get('degree')
    existing_req = request.form.get('existing_requirement')
    new_req = request.form.get('new_requirement')
    new_req_grade = request.form.get('new_requirement_grade')
    
    req_to_add = None
    
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if new_req:
            req_to_add = new_req
            cursor.execute("INSERT IGNORE INTO Requirements (requirement_name, minimum_grade) VALUES (%s, %s)", (new_req, new_req_grade))
        elif existing_req:
            req_to_add = existing_req
            
        if req_to_add and major and degree:
            cursor.execute("INSERT IGNORE INTO Program_Has_Requirements (major, degree, requirement_name) VALUES (%s, %s, %s)", (major, degree, req_to_add))
            
        conn.commit()
    except Exception as e:
        print(f"Error adding requirement to program: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
            
    return redirect(url_for('edit_program', major=major, degree=degree, requirement=req_to_add))

@app.route('/remove-requirement-from-program', methods=['POST'])
def remove_requirement_from_program():
    major = request.form.get('major')
    degree = request.form.get('degree')
    requirement = request.form.get('requirement')
    admin_password = request.form.get('admin_password')

    # Basic administrator protection
    if admin_password != os.environ.get('ADMIN_PASSWORD', 'admin'):
        return "Unauthorized: Incorrect admin password.", 403

    if major and degree and requirement:
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Program_Has_Requirements WHERE major = %s AND degree = %s AND requirement_name = %s",
                           (major, degree, requirement))
            conn.commit()
        except Exception as e:
            print(f"Error removing requirement from program: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

    # We deliberately omit 'requirement' here so the page resets the selected requirement dropdown
    return redirect(url_for('edit_program', major=major, degree=degree))

@app.route('/add-grouping', methods=['POST'])
def add_grouping():
    major = request.form.get('major')
    degree = request.form.get('degree')
    requirement = request.form.get('requirement')
    
    class_data = request.form.get('class_data')
    new_prefix = request.form.get('new_class_prefix')
    new_range = request.form.get('new_graduate_range')
    new_credits = request.form.get('new_credits')
    grouping_name = request.form.get('grouping_name')
    
    if requirement:
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            grouping_id_to_link = None

            if class_data and class_data.startswith("GROUPING|"):
                grouping_id_to_link = class_data.split('|')[1]
                
            elif class_data and class_data.startswith("CATALOG|"):
                parts = class_data.split('|')
                cat_prefix = parts[1]
                cat_number = parts[2]
                cat_credits = parts[3] if parts[3] != 'None' and parts[3] != '' else None
                
                g_name = grouping_name if grouping_name else f"{cat_prefix} {cat_number}"
                
                # Check if grouping name already exists
                cursor.execute("SELECT grouping_id FROM Class_Groupings WHERE grouping_name = %s", (g_name,))
                if cursor.fetchone():
                    return f"Error: A grouping with the name '{g_name}' already exists. Please choose a different name.", 400

                cursor.execute("INSERT INTO Class_Groupings (grouping_name, credits) VALUES (%s, %s)", (g_name, cat_credits))
                grouping_id_to_link = cursor.lastrowid
                
                cursor.execute("INSERT INTO Class_Grouping_Elements (grouping_id, class_prefix, min_class_number, max_class_number) VALUES (%s, %s, %s, %s)",
                               (grouping_id_to_link, cat_prefix, cat_number, cat_number))
                               
            elif grouping_name:
                # Check if grouping name already exists
                cursor.execute("SELECT grouping_id FROM Class_Groupings WHERE grouping_name = %s", (grouping_name,))
                if cursor.fetchone():
                    return f"Error: A grouping with the name '{grouping_name}' already exists. Please choose a different name.", 400

                cursor.execute("INSERT INTO Class_Groupings (grouping_name, credits) VALUES (%s, %s)",
                               (grouping_name, new_credits if new_credits != '' else None))
                grouping_id_to_link = cursor.lastrowid
                
                if new_prefix and new_range:
                    min_c, max_c = new_range.strip(), new_range.strip()
                    if '-' in new_range:
                        r_parts = new_range.split('-')
                        if len(r_parts) == 2 and r_parts[0].strip().isdigit() and r_parts[1].strip().isdigit():
                            min_c, max_c = r_parts[0].strip(), r_parts[1].strip()
                    cursor.execute("INSERT INTO Class_Grouping_Elements (grouping_id, class_prefix, min_class_number, max_class_number) VALUES (%s, %s, %s, %s)",
                                   (grouping_id_to_link, new_prefix.upper().strip(), min_c, max_c))
                                   
            if grouping_id_to_link:
                cursor.execute("INSERT IGNORE INTO Requirements_Composed_Of_Class_Groupings (requirement_name, grouping_id) VALUES (%s, %s)",
                               (requirement, grouping_id_to_link))
                conn.commit()
        except Exception as e:
            print(f"Error adding grouping: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
                
    return redirect(url_for('edit_program', major=major, degree=degree, requirement=requirement))

@app.route('/remove-grouping', methods=['POST'])
def remove_grouping():
    major = request.form.get('major')
    degree = request.form.get('degree')
    requirement = request.form.get('requirement')
    grouping_id = request.form.get('grouping_id')

    if requirement and grouping_id:
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Requirements_Composed_Of_Class_Groupings WHERE requirement_name = %s AND grouping_id = %s",
                           (requirement, grouping_id))
            
            conn.commit()
        except Exception as e:
            print(f"Error removing grouping: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

    return redirect(url_for('edit_program', major=major, degree=degree, requirement=requirement))

@app.route('/delete-requirement-global', methods=['POST'])
def delete_requirement_global():
    requirement = request.form.get('requirement')
    admin_password = request.form.get('admin_password')

    # Basic administrator protection
    if admin_password != os.environ.get('ADMIN_PASSWORD', 'admin'):
        return "Unauthorized: Incorrect admin password.", 403

    if requirement:
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check if requirement is used by any program
            cursor.execute("SELECT 1 FROM Program_Has_Requirements WHERE requirement_name = %s LIMIT 1", (requirement,))
            if not cursor.fetchone():
                # Requirement is not in use, safe to delete
                cursor.execute("DELETE FROM Requirements_Composed_Of_Class_Groupings WHERE requirement_name = %s", (requirement,))
                cursor.execute("DELETE FROM Requirements WHERE requirement_name = %s", (requirement,))
                conn.commit()
            else:
                print(f"Cannot delete requirement '{requirement}' because it is in use by one or more programs.")
        except Exception as e:
            print(f"Error deleting requirement from db: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

    return redirect(url_for('global_management'))

@app.route('/delete-grouping-global', methods=['POST'])
def delete_grouping_global():
    grouping_data = request.form.get('grouping')
    admin_password = request.form.get('admin_password')

    # Basic administrator protection
    if admin_password != os.environ.get('ADMIN_PASSWORD', 'admin'):
        return "Unauthorized: Incorrect admin password.", 403

    if grouping_data:
        parts = grouping_data.split('|')
        if len(parts) >= 2:
            grouping_id = parts[0]
            grouping_name = parts[1]
            
            conn = None
            cursor = None
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                # Check if grouping is used by any requirement
                cursor.execute("SELECT 1 FROM Requirements_Composed_Of_Class_Groupings WHERE grouping_id = %s LIMIT 1", (grouping_id,))
                if not cursor.fetchone():
                    # Grouping is not in use, safe to delete
                    cursor.execute("DELETE FROM Class_Groupings WHERE grouping_id = %s", (grouping_id,))
                    conn.commit()                    
                else:
                    print(f"Cannot delete grouping '{grouping_name}' because it is in use by one or more requirements.")
            except Exception as e:
                print(f"Error deleting grouping from db: {e}")
            finally:
                if cursor:
                    cursor.close()
                if conn and conn.is_connected():
                    conn.close()

    return redirect(url_for('global_management'))

@app.route('/delete-program', methods=['POST'])
def delete_program():
    major = request.form.get('major')
    degree = request.form.get('degree')
    admin_password = request.form.get('admin_password')

    # Basic administrator protection
    if admin_password != os.environ.get('ADMIN_PASSWORD', 'admin'):
        return "Unauthorized: Incorrect admin password.", 403

    if major and degree:
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Program WHERE major = %s AND degree = %s", (major, degree))
            conn.commit()
        except Exception as e:
            print(f"Error deleting program: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

    return redirect(url_for('edit_program'))

@app.route('/add-class-to-catalog', methods=['POST'])
def add_class_to_catalog():
    class_prefix = request.form.get('class_prefix')
    class_number = request.form.get('class_number')
    class_title = request.form.get('class_title')
    credits = request.form.get('credits')
    admin_password = request.form.get('admin_password')

    if admin_password != os.environ.get('ADMIN_PASSWORD', 'admin'):
        return "Unauthorized: Incorrect admin password.", 403

    if class_prefix and class_number:
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("INSERT IGNORE INTO Class (class_prefix, class_number) VALUES (%s, %s)", (class_prefix.upper(), class_number))
            
            credits_val = int(credits) if credits and credits.isdigit() else None
            cursor.execute("""
                INSERT IGNORE INTO Class_Catalog (class_prefix, graduate_class_number, class_title, credits) 
                VALUES (%s, %s, %s, %s)
            """, (class_prefix.upper(), class_number, class_title, credits_val))
            conn.commit()
        except Exception as e:
            print(f"Error adding class to catalog: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

    return redirect(url_for('global_management'))

@app.route('/delete-class-from-catalog', methods=['POST'])
def delete_class_from_catalog():
    catalog_class = request.form.get('catalog_class')
    admin_password = request.form.get('admin_password')

    if admin_password != os.environ.get('ADMIN_PASSWORD', 'admin'):
        return "Unauthorized: Incorrect admin password.", 403

    if catalog_class:
        parts = catalog_class.split('|')
        if len(parts) >= 2:
            class_prefix = parts[0]
            class_number = parts[1]
            
            conn = None
            cursor = None
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                # Check if the class is used in any plan
                cursor.execute("SELECT 1 FROM Plan_Requires_Class WHERE class_prefix = %s AND class_number = %s LIMIT 1", (class_prefix, class_number))
                if not cursor.fetchone():
                    cursor.execute("DELETE FROM Class_Catalog WHERE class_prefix = %s AND graduate_class_number = %s", (class_prefix, class_number))
                    conn.commit()
                else:
                    print(f"Cannot delete class '{class_prefix} {class_number}' because it is in use by one or more plans.")
            except Exception as e:
                print(f"Error deleting class from catalog: {e}")
            finally:
                if cursor:
                    cursor.close()
                if conn and conn.is_connected():
                    conn.close()

    return redirect(url_for('global_management'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)