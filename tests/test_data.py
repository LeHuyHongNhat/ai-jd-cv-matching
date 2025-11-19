"""Sample data cho testing"""

SAMPLE_CV_TEXT = """
Le Huy Hong Nhat
 nhat050403@gmail.com
 +84949794366
 github.com/LeHuyHongNhat
 linkedin.com/in/lenhat543-it
 Career Objective
 Seeking an AI Engineer internship opportunity to apply my knowledge in Machine Learning and Deep Learning
 to solve real-world problems. Eager to learn new technologies and enhance software development skills in a
 professional environment.
 Education
 Posts and Telecommunications Institute of Technology- PTIT
 Major: Information Systems
 Sep 2021- Present
 • Key Courses: Python Programming, Machine Learning, Natural Language Processing, Computer Vision, Data
 Science
 Work Experience
 AI Engineer Intern at Insight Data
 Oct 2024– Dec 2024
 • Developed a chatbot system for automatic message response using LangChain, LLM, and Vector Database
 • Applied the Retrieval-Augmented Generation (RAG) technique to enhance answer relevance using
 context-aware retrieval
 • Utilized Prompt Engineering methods to refine LLM prompts for higher response quality and coherence
 • Built RESTful APIs using FastAPI to support chatbot integration and backend communication
 Featured Projects
 Soccer Player Image Classification with ResNet18
 Computer Vision
 • Developed and trained ResNet18 network for soccer player image classification, achieving 96% accuracy
 • Implemented Learning Rate Scheduling and Data Augmentation for model optimization
 • Deployed and optimized performance on Kaggle platform
 Football Ball Speed Estimation App
 Computer Vision & Mobile Development
 • Collaborating with a freelancer group to build an application that measures the speed of a soccer ball’s kick
 using state-of-the-art models like YOLO and DeTR
• Applied image processing algorithms to accurately compute ball speed from mobile cameras on both Android
 and iOS platforms
 • Collected real-world kicking data under diverse conditions including different weather scenarios, deformed balls,
 small-sized balls, partially occluded balls, and motion blur caused by powerful kicks
 • Continuously optimizing model performance and accuracy through testing and algorithm enhancements
 Data Mining System
 Data Science & Full-Stack
 • Built a comprehensive data mining web application with a FastAPI backend and an interactive frontend
 interface
 • Implemented robust data preprocessing pipeline including missing value imputation, outlier detection, feature
 scaling, and encoding
 • Integrated multiple machine learning algorithms (Random Forest, XGBoost, SVM, Neural Network, etc.) for
 classification, regression, and clustering
 • Designed evaluation module with cross-validation, hyperparameter tuning, and explainability using SHAP
 • Developed RESTful API endpoints for data upload, model training, and preprocessing; deployed system locally
 with Uvicorn
 Vietnamese Sentiment Analysis with PhoBERT
 • Developed sentiment classification model using PhoBERTbase with 93.8% accuracy
 • Utilized UIT-VSFC dataset combined with 8,000+ self-collected and labeled real-world samples
 • Optimized model performance through Learning Rate Scheduling and imbalanced data handling
 Restaurant Customer Service Chatbot
 NLP
 NLP & Flask
 • Designed intelligent chatbot using a 2-hidden-layer neural network architecture
 • Integrated Word2Vec and Attention Mechanism to enhance response accuracy
 • Implemented lightweight solution suitable for small-scale systems
 Healthcare Chatbot with LLM
 • Built RAG (Retrieval-Augmented Generation) chatbot using LangChain
 • Applied Prompt Engineering techniques to optimize response accuracy
 • Designed vector database for efficient query processing
 Flower Search System
 LLM & LangChain & FastAPI
 Computer Vision & Full-Stack
 • Developed a content-based image retrieval system for flowers using deep learning and vector similarity search
 • Extracted image features with a pre-trained ResNet50 model and stored vectors in ChromaDB for similarity
 comparison
 • Built a full-stack solution with a FastAPI backend and Streamlit frontend, allowing users to upload images
 and retrieve top similar results with similarity scores
 • Implemented a standardized image preprocessing pipeline and designed system evaluation using precision,
 recall, and mAP
 • Created modular components including preprocessing, feature extraction, vector database, and evaluation
 scripts
 Skills
Technical Skills
 Soft Skills
 • Languages: Python, Java, C++
 • Frameworks: PyTorch, Scikit-learn, TensorFlow,
 Keras, LangChain, Flask, FastAPI, Streamlit
 • Databases: MySQL, MongoDB, SQL Server, Neo4j
 • Tools: Git, Docker
 • AI/ML: NLP, Computer Vision, LLM
 • Language: Proficient in English (reading, writing,
 listening)
 • Communication: Strong interpersonal skills
 • Teamwork: Experienced in team management
 • Leadership: Led multiple academic project team
"""

SAMPLE_JD_TEXT = """
Job Description

Participate in the development of neural network, machine learning, NLP, and big data technologies for company products such as chatbots, search engines, and data analysis systems. 
Collect, clean, and prepare large-scale datasets for training AI models. 
Research and apply machine learning, deep learning, and big data technologies to build and enhance AI solutions. 
Evaluate model performance and propose optimization solutions. 
Develop and maintain AI related functions and features using C# and Python. 
Support other team members in projects and products implementation, particularly in integrating AI with big data technologies. 
Leverage and integration with AI services in cloud platforms, such as Google, AWS, Azure.

Requirements

Bachelor’s degree in computer science, information technology, data science or a related field. 
Solid understanding of probability and statistics, discrete mathematics, and linear algebra. 
Knowledge of algorithms and data structures. 
Experience with at least one framework or library (e.g., TensorFlow, PyTorch) and one programming language (Python and C# preferred). 
Knowledge of big data processing tools like Hadoop and Spark, including concepts such as MapReduce and data parallelism. 
Strong learning attitude, enthusiasm for research and a passion for exploring new AI and big data technologies. 
Good communication skills and ability to work effectively in a team. 
Good English communication. 

Preferred

Experience participating in neural network, machine learning, NLP, big data related projects. 
Experience working with distributed databases, vector database and big data storage solutions.
"""

# Structured data mẫu để test
EXPECTED_CV_STRUCTURED = {
    "full_name": "Nguyễn Văn A",
    "email": "nguyenvana@email.com",
    "phone": "0123456789",
    "skills": ["Python", "JavaScript", "TypeScript", "FastAPI", "Django", "Flask", "React", "Vue.js", "PostgreSQL", "MongoDB", "Redis", "Docker", "Kubernetes", "Git", "CI/CD"],
    "job_titles": ["Software Engineer", "Junior Developer"],
    "degrees": ["Cử nhân Công nghệ Thông tin - Đại học Bách Khoa"],
    "certifications": ["AWS Certified Solutions Architect", "Google Cloud Professional Developer"]
}

EXPECTED_JD_STRUCTURED = {
    "skills": ["Python", "FastAPI", "PostgreSQL", "React", "Vue.js", "Docker", "Kubernetes"],
    "job_titles": ["Senior Software Engineer", "Software Engineer", "Senior Developer"],
    "degrees": ["Cử nhân Công nghệ Thông tin"],
    "certifications": ["AWS", "GCP"]
}

