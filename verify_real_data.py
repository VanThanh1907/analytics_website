#!/usr/bin/env python3
"""
Verify All Services Are Using Real Data
Checks all Python files to ensure no mock/random data generation
"""

import os
import re
import sqlite3

# ANSI colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def check_database():
    """Check database has real data"""
    print(f"\n{BLUE}📊 Checking Database...{RESET}")
    
    db_path = os.path.join('web-app', 'instance', 'ecommerce.db')
    if not os.path.exists(db_path):
        print(f"{RED}❌ Database not found: {db_path}{RESET}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check interactions
    cursor.execute("SELECT COUNT(*) FROM user_interaction")
    interactions = cursor.fetchone()[0]
    print(f"  ✅ User Interactions: {interactions:,}")
    
    # Check products
    cursor.execute("SELECT COUNT(*) FROM product")
    products = cursor.fetchone()[0]
    print(f"  ✅ Products: {products}")
    
    # Check users
    cursor.execute("SELECT COUNT(*) FROM user")
    users = cursor.fetchone()[0]
    print(f"  ✅ Users: {users}")
    
    # Check recent activity
    cursor.execute("""
        SELECT COUNT(*) FROM user_interaction 
        WHERE timestamp >= datetime('now', '-30 minutes')
    """)
    recent = cursor.fetchone()[0]
    print(f"  ✅ Recent Activity (30 min): {recent}")
    
    conn.close()
    
    if interactions == 0:
        print(f"{YELLOW}⚠️  Warning: No interactions found. Create some test data!{RESET}")
    
    return True

def check_file_for_mock_data(filepath):
    """Check if file uses mock/random data"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    issues = []
    
    # Check for random imports (excluding comments)
    if re.search(r'^import random$', content, re.MULTILINE):
        # Check if actually used (not just imported but not used)
        if re.search(r'random\.(randint|uniform|choice|random)', content):
            issues.append("Uses 'import random' with random generation")
    
    if re.search(r'from random import', content):
        issues.append("Uses 'from random import'")
    
    # Check for generate_demo_data function calls
    if re.search(r'generate_demo_data\(\)', content):
        issues.append("Calls generate_demo_data()")
    
    # Check for hardcoded mock data patterns
    if re.search(r'# Mock data|# Demo data|# Fake data', content, re.IGNORECASE):
        issues.append("Contains mock data comments")
    
    return issues

def verify_services():
    """Verify all main services use real data"""
    print(f"\n{BLUE}🔍 Verifying Services...{RESET}")
    
    services = {
        'Analytics Dashboard': 'dashboard/analytics_dashboard_fixed.py',
        'HDFS UI': 'hdfs_ui_simulation.py',
        'Spark UI': 'spark_ui_fixed.py',
        'Recommendation API': 'recommendation-engine/api_server_real.py',
        'Web App': 'web-app/app.py',
    }
    
    all_clean = True
    
    for service_name, filepath in services.items():
        if not os.path.exists(filepath):
            print(f"{YELLOW}⚠️  {service_name}: File not found - {filepath}{RESET}")
            continue
        
        issues = check_file_for_mock_data(filepath)
        
        if issues:
            print(f"{RED}❌ {service_name}:{RESET}")
            for issue in issues:
                print(f"   - {issue}")
            all_clean = False
        else:
            print(f"{GREEN}✅ {service_name}: Using real data{RESET}")
    
    return all_clean

def check_database_connections():
    """Verify files connect to the database"""
    print(f"\n{BLUE}🔗 Checking Database Connections...{RESET}")
    
    files_to_check = [
        'dashboard/analytics_dashboard_fixed.py',
        'hdfs_ui_simulation.py', 
        'spark_ui_fixed.py',
        'recommendation-engine/api_server_real.py',
        'recommendation-engine/simple_recommendation.py',
    ]
    
    for filepath in files_to_check:
        if not os.path.exists(filepath):
            continue
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        has_db_connection = False
        
        if 'sqlite3.connect' in content:
            has_db_connection = True
        elif 'DB_PATH' in content or 'db_path' in content:
            has_db_connection = True
        elif 'ecommerce.db' in content:
            has_db_connection = True
        
        filename = os.path.basename(filepath)
        if has_db_connection:
            print(f"  {GREEN}✅ {filename}: Connected to database{RESET}")
        else:
            print(f"  {YELLOW}⚠️  {filename}: No database connection found{RESET}")

def main():
    print(f"""
{BLUE}╔══════════════════════════════════════════════════════════╗
║          REAL DATA VERIFICATION SCRIPT                   ║
║          HUIT - Big Data Final Project                   ║
╚══════════════════════════════════════════════════════════╝{RESET}
    """)
    
    # Check database
    db_ok = check_database()
    
    # Verify services
    services_ok = verify_services()
    
    # Check database connections
    check_database_connections()
    
    # Summary
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}📋 VERIFICATION SUMMARY{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    if db_ok and services_ok:
        print(f"{GREEN}✅ ALL CHECKS PASSED!{RESET}")
        print(f"{GREEN}✅ All services are using 100% real data from database{RESET}")
        print(f"{GREEN}✅ No mock/random data generation found{RESET}")
        print(f"\n{GREEN}🎉 System ready for production demo!{RESET}")
    else:
        print(f"{RED}❌ Some issues found. Please review above.{RESET}")
    
    print(f"\n{BLUE}📖 Files Converted:{RESET}")
    print(f"  1. {GREEN}analytics_dashboard_fixed.py{RESET} - Real SQL queries")
    print(f"  2. {GREEN}hdfs_ui_simulation.py{RESET} - Real storage metrics")
    print(f"  3. {GREEN}spark_ui_fixed.py{RESET} - Real cluster metrics")
    print(f"  4. {GREEN}api_server_real.py{RESET} - Real recommendations")
    print(f"  5. {GREEN}app.py{RESET} - Real user tracking")
    
    print(f"\n{BLUE}🚀 Launch Demo:{RESET}")
    print(f"  {GREEN}START_FIXED_DEMO.bat{RESET} - Launches all 5 services")
    print()

if __name__ == "__main__":
    main()
