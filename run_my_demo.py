"""
Script để chạy demo với CV và JD thực tế
"""
from pathlib import Path
from demo_matching import CVJDMatchingDemo


def main():
    # Đường dẫn cố định
    cv_folder = r"D:\Python Projects\GP\input\cvs"
    jd_folder = r"D:\Python Projects\GP\input\jds"
    
    print("=" * 80)
    print("CV-JD MATCHING DEMO - RUNNING WITH YOUR DATA")
    print("=" * 80)
    print(f"\nCV Folder: {cv_folder}")
    print(f"JD Folder: {jd_folder}")
    
    # Kiểm tra folders tồn tại
    cv_path = Path(cv_folder)
    jd_path = Path(jd_folder)
    
    if not cv_path.exists():
        print(f"\n❌ Error: CV folder not found: {cv_folder}")
        return
    
    if not jd_path.exists():
        print(f"\n❌ Error: JD folder not found: {jd_folder}")
        return
    
    # Liệt kê các file
    cv_files = list(cv_path.glob("*.pdf")) + list(cv_path.glob("*.docx"))
    jd_files = list(jd_path.glob("*.pdf")) + list(jd_path.glob("*.docx"))
    
    print(f"\n📁 Found {len(cv_files)} CV files:")
    for cv_file in cv_files:
        print(f"   • {cv_file.name}")
    
    print(f"\n📁 Found {len(jd_files)} JD files:")
    for jd_file in jd_files:
        print(f"   • {jd_file.name}")
    
    if not cv_files:
        print("\n❌ No CV files found!")
        return
    
    if not jd_files:
        print("\n❌ No JD files found!")
        return
    
    # Chọn JD để match
    print(f"\n{'='*80}")
    if len(jd_files) == 1:
        selected_jd = jd_files[0]
        print(f"Using JD: {selected_jd.name}")
    else:
        print("Select JD file to use:")
        for i, jd_file in enumerate(jd_files, 1):
            print(f"  {i}. {jd_file.name}")
        
        while True:
            try:
                choice = input("\nEnter number (or press Enter for first JD): ").strip()
                if choice == "":
                    selected_jd = jd_files[0]
                    break
                choice_num = int(choice)
                if 1 <= choice_num <= len(jd_files):
                    selected_jd = jd_files[choice_num - 1]
                    break
                else:
                    print(f"Please enter a number between 1 and {len(jd_files)}")
            except ValueError:
                print("Invalid input. Please enter a number.")
    
    print(f"\n✓ Selected JD: {selected_jd.name}")
    
    # Xác nhận trước khi chạy
    print(f"\n{'='*80}")
    print(f"READY TO RUN:")
    print(f"  • Will process {len(cv_files)} CVs")
    print(f"  • Will match against: {selected_jd.name}")
    print(f"  • Estimated time: ~{len(cv_files) * 15} seconds")
    print(f"  • API calls: ~{len(cv_files) * 3} calls to OpenAI")
    print(f"{'='*80}")
    
    proceed = input("\nProceed? (y/n): ").strip().lower()
    if proceed != 'y':
        print("❌ Demo cancelled")
        return
    
    # Chạy demo
    print(f"\n{'='*80}")
    print("STARTING DEMO...")
    print(f"{'='*80}")
    
    demo = CVJDMatchingDemo()
    demo.run_demo(cv_folder, str(selected_jd))
    
    print(f"\n{'='*80}")
    print("✅ DEMO COMPLETED SUCCESSFULLY!")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()

