import json
import random
import os
from datetime import datetime
from pathlib import Path

# Data pools for generating CVs - Mở rộng để tránh trùng lặp
FIRST_NAMES = ["Nguyen", "Tran", "Le", "Pham", "Hoang", "Vu", "Dang", "Bui", "Do", "Ngo", 
               "Duong", "Ly", "Vo", "Truong", "Phan", "Tang", "Lam", "Ha", "Dinh", "Cao"]
MIDDLE_NAMES = ["Van", "Thi", "Duc", "Minh", "Hoang", "Anh", "Thanh", "Quoc", "Hong", "Kim",
                "Ngoc", "Xuan", "Thu", "Hai", "Huu", "Tuan", "Duy", "Khanh", "Bao", "Phuong"]
LAST_NAMES = ["An", "Binh", "Cuong", "Dung", "Hieu", "Khang", "Long", "Nam", "Phong", "Tuan", 
              "Vy", "Yen", "Linh", "Mai", "Trang", "Hoa", "Sang", "Dat", "Quan", "Tai", 
              "Thao", "Trung", "Hung", "Hai", "Son", "Thang", "Huong", "Nhi", "Kien", "Lam"]

TECH_ROLES = [
    "Backend Developer", "Frontend Developer", "Full-Stack Developer",
    "Data Scientist", "ML Engineer", "DevOps Engineer",
    "Mobile Developer", "Cloud Architect", "QA Engineer", "Security Engineer",
    "Data Engineer", "AI Engineer", "Site Reliability Engineer", "Platform Engineer",
    "Software Architect", "Systems Engineer", "Automation Engineer", "Blockchain Developer",
    "Game Developer", "Embedded Systems Engineer"
]

PROGRAMMING_LANGS = [
    "Python", "Java", "JavaScript", "C++", "Go", "Rust", "TypeScript", "PHP", "C#", 
    "Kotlin", "Swift", "Ruby", "Scala", "R", "Dart", "Perl", "Shell", "Objective-C",
    "Elixir", "Haskell", "Clojure", "Julia", "MATLAB"
]

FRAMEWORKS = [
    "React", "Angular", "Vue.js", "Django", "Flask", "FastAPI", "Spring Boot", 
    "Node.js", "Express.js", "PyTorch", "TensorFlow", "Scikit-learn", "Keras",
    "Next.js", "Nuxt.js", "Laravel", "Symfony", "ASP.NET", "Ruby on Rails",
    "Svelte", "Gin", "Echo", "Fiber", "NestJS", "Quarkus", "Micronaut",
    "Streamlit", "Pandas", "NumPy", "Apache Spark", "Hadoop"
]

TOOLS = [
    "Git", "Docker", "Kubernetes", "Jenkins", "AWS", "Azure", "GCP", "Terraform", 
    "Ansible", "Jira", "GitLab CI/CD", "CircleCI", "Travis CI", "Prometheus",
    "Grafana", "ELK Stack", "Datadog", "New Relic", "Selenium", "Postman",
    "SonarQube", "Splunk", "Consul", "Vault", "Rancher", "ArgoCD", "Helm",
    "Vagrant", "Chef", "Puppet", "Redis", "RabbitMQ", "Kafka", "Nginx"
]

DATABASES = [
    "MySQL", "PostgreSQL", "MongoDB", "Redis", "Cassandra", "Neo4j", "DynamoDB", 
    "Oracle", "SQL Server", "MariaDB", "CouchDB", "InfluxDB", "Elasticsearch",
    "Firebase", "Supabase", "TimeScaleDB", "ClickHouse", "Snowflake", "BigQuery"
]

COMPANIES = [
    "FPT Software", "Viettel", "VNG Corporation", "Tiki", "Shopee", "Grab", 
    "Momo", "VinID", "CMC Corporation", "TMA Solutions", "Nash Tech", "ELCA",
    "KMS Technology", "Axon Active", "TPS Software", "Framgia", "Savvycom",
    "Orient Software", "NITECO", "Luxoft", "EPAM", "Cognizant", "Accenture",
    "Tech Mahindra", "NTT Data", "Katalon", "Be Group", "VNPay", "ZaloPay",
    "Techcombank", "BIDV", "VPBank"
]

INDUSTRIES = [
    "E-commerce", "Fintech", "Telecommunications", "Healthcare", "Education", 
    "Logistics", "Gaming", "Social Media", "IoT", "Cybersecurity", "Banking",
    "Insurance", "Retail", "Manufacturing", "Real Estate", "Transportation",
    "Media & Entertainment", "Travel & Hospitality", "Agriculture", "Energy"
]

UNIVERSITIES = [
    "Hanoi University of Science and Technology",
    "Vietnam National University",
    "Posts and Telecommunications Institute of Technology",
    "FPT University",
    "University of Information Technology - VNU-HCM",
    "Da Nang University of Technology",
    "Can Tho University",
    "Hue University",
    "Ton Duc Thang University",
    "HCMC University of Technology and Education",
    "Duy Tan University",
    "Phenikaa University",
    "International University - VNU-HCM",
    "RMIT University Vietnam",
    "British University Vietnam"
]

CERTIFICATIONS = [
    "AWS Certified Solutions Architect",
    "AWS Certified Developer",
    "Google Cloud Professional",
    "Azure Fundamentals",
    "Certified Kubernetes Administrator",
    "Azure DevOps Engineer Expert",
    "Oracle Certified Professional",
    "CISSP - Certified Information Systems Security Professional",
    "PMP - Project Management Professional",
    "Certified Scrum Master",
    "Certified Ethical Hacker",
    "CompTIA Security+",
    "TensorFlow Developer Certificate",
    "Professional Data Engineer",
    "HashiCorp Certified: Terraform Associate"
]

# Mở rộng danh sách để tạo đa dạng
RESPONSIBILITIES_POOL = [
    "Developed and maintained {} applications",
    "Designed and implemented scalable {} solutions",
    "Led development of {} platform from scratch",
    "Optimized {} system performance and reliability",
    "Built and deployed {} microservices architecture",
    "Collaborated with cross-functional teams of {} members",
    "Participated in code reviews and technical discussions",
    "Mentored junior developers on best practices",
    "Implemented CI/CD pipelines for automated deployments",
    "Conducted system design and architecture reviews",
    "Managed database design and optimization",
    "Integrated third-party APIs and services",
    "Implemented security best practices and compliance",
    "Created technical documentation and user guides",
    "Performed troubleshooting and bug fixes"
]

ACHIEVEMENTS_POOL = [
    "Improved system performance by {}%",
    "Reduced deployment time by {}%",
    "Increased test coverage from {}% to {}%",
    "Led team of {} developers on major project",
    "Reduced infrastructure costs by {}%",
    "Decreased bug rate by {}%",
    "Improved API response time by {}ms",
    "Achieved {}% customer satisfaction rating",
    "Successfully migrated {} users to new platform",
    "Implemented feature that increased revenue by {}%",
    "Reduced server response time from {}s to {}s",
    "Scaled system to handle {}M requests per day",
    "Automated {} manual processes",
    "Won 'Best Developer' award in Q{} 20{}"
]

PROJECT_TYPES = [
    "E-commerce platform", "Payment gateway", "Data analytics dashboard",
    "Mobile application", "Cloud migration", "Microservices architecture",
    "Real-time chat system", "Content management system", "API gateway",
    "Machine learning pipeline", "Data warehouse", "Inventory management system",
    "Customer relationship management", "Human resource management",
    "Booking and reservation system", "Social media platform",
    "Video streaming service", "IoT monitoring dashboard", "Supply chain management",
    "Financial trading platform", "Healthcare management system"
]

SOFT_SKILLS_POOL = {
    "communication": [
        "Effective communication", "Public speaking", "Technical writing",
        "Active listening", "Cross-cultural communication", "Presentation skills",
        "Negotiation skills", "Stakeholder management", "Client relationship"
    ],
    "teamwork": [
        "Team collaboration", "Cross-functional teamwork", "Pair programming",
        "Code review facilitation", "Remote collaboration", "Agile teamwork",
        "Conflict resolution", "Team building"
    ],
    "leadership": [
        "Team leadership", "Project management", "Mentoring junior developers",
        "Agile leadership", "Decision making", "Strategic planning",
        "Technical leadership", "People management", "Vision setting"
    ],
    "problem_solving": [
        "Analytical thinking", "Critical thinking", "Debugging complex systems",
        "Algorithm optimization", "Root cause analysis", "Creative problem solving",
        "Systems thinking", "Troubleshooting", "Performance optimization"
    ],
    "adaptability": [
        "Quick learner", "Adaptive to new technologies", "Flexible mindset",
        "Open to feedback", "Continuous learning", "Growth mindset",
        "Change management", "Innovation"
    ]
}

def generate_name():
    return f"{FIRST_NAMES[random.randint(0, len(FIRST_NAMES)-1)]} {MIDDLE_NAMES[random.randint(0, len(MIDDLE_NAMES)-1)]} {LAST_NAMES[random.randint(0, len(LAST_NAMES)-1)]}"

def generate_email(name):
    clean_name = name.lower().replace(" ", "")
    domains = ["gmail.com", "outlook.com", "yahoo.com", "protonmail.com"]
    return f"{clean_name}{random.randint(100, 999)}@{random.choice(domains)}"

def generate_phone():
    return f"+84{random.randint(900000000, 999999999)}"

def generate_cv_data(index):
    # Sử dụng seed để đảm bảo mỗi CV unique nhưng reproducible
    random.seed(index * 42)
    
    name = generate_name()
    email = generate_email(name)
    phone = generate_phone()
    
    # Select role and relevant skills
    role = random.choice(TECH_ROLES)
    years_exp = round(random.uniform(0.5, 12.0), 1)
    
    # Generate skills based on role - đa dạng hơn
    num_langs = random.randint(2, 5)
    num_frameworks = random.randint(3, 8)
    num_tools = random.randint(3, 6)
    num_dbs = random.randint(1, 4)
    
    prog_langs = random.sample(PROGRAMMING_LANGS, min(num_langs, len(PROGRAMMING_LANGS)))
    frameworks = random.sample(FRAMEWORKS, min(num_frameworks, len(FRAMEWORKS)))
    tools = random.sample(TOOLS, min(num_tools, len(TOOLS)))
    dbs = random.sample(DATABASES, min(num_dbs, len(DATABASES)))
    
    # Certifications - đa dạng hơn
    num_certs = random.choices([0, 1, 2, 3], weights=[20, 40, 30, 10])[0]
    certs = random.sample(CERTIFICATIONS, min(num_certs, len(CERTIFICATIONS))) if num_certs > 0 else []
    
    # Work experience - đa dạng hơn
    num_jobs = random.randint(1, 5)
    companies = random.sample(COMPANIES, min(num_jobs, len(COMPANIES)))
    industries = random.sample(INDUSTRIES, min(num_jobs, len(INDUSTRIES)))
    
    # Generate diverse responsibilities
    app_types = ["web", "mobile", "cloud", "desktop", "enterprise", "distributed"]
    responsibilities = []
    for template in random.sample(RESPONSIBILITIES_POOL, random.randint(3, 6)):
        if "{}" in template:
            if "teams" in template or "developers" in template:
                resp = template.format(random.randint(3, 20))
            elif "applications" in template or "solutions" in template:
                resp = template.format(random.choice(app_types))
            else:
                resp = template.format(random.choice(app_types))
        else:
            resp = template
        responsibilities.append(resp)
    
    # Generate diverse achievements
    achievements = []
    for template in random.sample(ACHIEVEMENTS_POOL, random.randint(2, 5)):
        if "performance by" in template or "costs by" in template or "bug rate" in template:
            achievement = template.format(random.randint(15, 70))
        elif "deployment time" in template:
            achievement = template.format(random.randint(20, 80))
        elif "test coverage" in template:
            old_cov = random.randint(20, 60)
            new_cov = random.randint(old_cov + 20, 95)
            achievement = template.format(old_cov, new_cov)
        elif "team of" in template:
            achievement = template.format(random.randint(2, 12))
        elif "response time" in template:
            if "API" in template:
                achievement = template.format(random.randint(50, 500))
            else:
                old_time = round(random.uniform(2.0, 10.0), 1)
                new_time = round(random.uniform(0.1, old_time * 0.5), 2)
                achievement = template.format(old_time, new_time)
        elif "users" in template:
            achievement = template.format(random.randint(10, 500) * 1000)
        elif "revenue" in template or "satisfaction" in template:
            achievement = template.format(random.randint(10, 50))
        elif "requests per day" in template:
            achievement = template.format(random.randint(1, 100))
        elif "processes" in template:
            achievement = template.format(random.randint(5, 30))
        elif "award" in template:
            achievement = template.format(random.randint(1, 4), random.randint(20, 24))
        else:
            achievement = template
        achievements.append(achievement)
    
    # Education - đa dạng hơn
    university = random.choice(UNIVERSITIES)
    majors = [
        "Computer Science", "Software Engineering", "Information Technology", 
        "Data Science", "Computer Engineering", "Artificial Intelligence",
        "Cybersecurity", "Information Systems", "Electronics and Telecommunications"
    ]
    major = random.choice(majors)
    degree = random.choices(
        ["Bachelor", "Master", "Ph.D."], 
        weights=[70, 25, 5]
    )[0]
    
    # Additional courses
    course_pool = [
        "AWS Cloud Practitioner", "Docker & Kubernetes", 
        "Machine Learning Bootcamp", "Agile Scrum Master",
        "Deep Learning Specialization", "Data Structures and Algorithms",
        "System Design", "Microservices Architecture", "GraphQL",
        "React Advanced", "Cloud Native Development", "DevSecOps"
    ]
    num_courses = random.randint(0, 4)
    additional_courses = random.sample(course_pool, min(num_courses, len(course_pool)))
    
    # Soft skills - lấy từ pool đa dạng
    comm_skills = random.sample(SOFT_SKILLS_POOL["communication"], random.randint(2, 4))
    teamwork_skills = random.sample(SOFT_SKILLS_POOL["teamwork"], random.randint(1, 3))
    leadership_skills = random.sample(SOFT_SKILLS_POOL["leadership"], random.randint(1, 3))
    problem_skills = random.sample(SOFT_SKILLS_POOL["problem_solving"], random.randint(2, 4))
    adapt_skills = random.sample(SOFT_SKILLS_POOL["adaptability"], random.randint(1, 3))
    
    # Language proficiency - đa dạng hơn
    lang_options = [
        ["Vietnamese (Native)", "English (Fluent)"],
        ["Vietnamese (Native)", "English (Advanced)"],
        ["Vietnamese (Native)", "English (Intermediate)"],
        ["Vietnamese (Native)", "English (Fluent)", "Japanese (Intermediate)"],
        ["Vietnamese (Native)", "English (Advanced)", "Chinese (Basic)"],
        ["Vietnamese (Native)", "English (Fluent)", "Korean (Basic)"]
    ]
    languages = random.choice(lang_options)
    
    # Industry specific skills
    industry_skills = [
        f"{role.split()[0]} development",
        "API design",
        "Code review",
        random.choice(["RESTful APIs", "GraphQL", "gRPC", "WebSocket"]),
        random.choice(["Unit testing", "Integration testing", "E2E testing"]),
        random.choice(["Agile/Scrum", "Kanban", "DevOps practices"])
    ]
    
    # Generate JSON structure
    json_data = {
        "full_name": name,
        "email": email,
        "phone": phone,
        "hard_skills": {
            "programming_languages": prog_langs,
            "technologies_frameworks": frameworks,
            "tools_software": tools,
            "certifications": certs,
            "industry_specific_skills": random.sample(industry_skills, random.randint(3, len(industry_skills)))
        },
        "work_experience": {
            "total_years": years_exp,
            "job_titles": [role, f"Senior {role}" if years_exp > 3 else f"Junior {role}"],
            "industries": industries,
            "companies": companies,
            "company_sizes": random.sample(["Startup", "SME", "Enterprise"], random.randint(1, 3))
        },
        "responsibilities_achievements": {
            "key_responsibilities": responsibilities,
            "achievements": achievements,
            "project_types": random.sample(PROJECT_TYPES, random.randint(2, 5))
        },
        "soft_skills": {
            "communication_teamwork": comm_skills + teamwork_skills,
            "leadership_management": leadership_skills,
            "problem_solving": problem_skills,
            "adaptability": adapt_skills
        },
        "education_training": {
            "degrees": [f"{degree} of Science"],
            "majors": [major],
            "universities": [university],
            "additional_courses": additional_courses
        },
        "additional_factors": {
            "languages": languages,
            "availability": random.choice(["Immediate", "1 month notice", "2 weeks notice", "Negotiable"]),
            "relocation_willingness": random.choice([True, False]),
            "travel_willingness": random.choice([True, False]),
            "expected_salary": f"${random.randint(600, 3500)}/month"
        },
        "skills": prog_langs + frameworks + tools,
        "job_titles": [role],
        "degrees": [f"{degree} of Science in {major}"],
        "certifications": certs
    }
    
    # Reset seed để các CV tiếp theo vẫn random
    random.seed()
    
    return json_data

# Tạo thư mục output nếu chưa có
output_dir = Path(__file__).parent / "generated"
output_dir.mkdir(exist_ok=True)

# Generate và lưu 100 CVs
generated_files = []

for i in range(1, 101):
    cv_data = generate_cv_data(i)
    
    # Tạo tên file
    name_slug = cv_data['full_name'].replace(' ', '_')
    json_filename = f"cv_{i:03d}_{name_slug}.json"  # 3 chữ số cho 100 CV
    json_path = output_dir / json_filename
    
    # Lưu file JSON
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(cv_data, f, indent=2, ensure_ascii=False)
    
    generated_files.append({
        'number': i,
        'name': cv_data['full_name'],
        'role': cv_data['work_experience']['job_titles'][0],
        'json_file': json_filename
    })

# In báo cáo
print(f"\nĐã tạo {len(generated_files)} file CV tại: {output_dir}")
print("\nDanh sách 10 file đầu tiên:")
print("-" * 80)
for item in generated_files[:10]:
    print(f"{item['number']:3d}. {item['name']:30s} - {item['role']:25s}")
    print(f"     File: {item['json_file']}")
print("-" * 80)
print(f"\n... và {len(generated_files) - 10} file khác")
print("-" * 80)