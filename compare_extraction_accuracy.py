"""
Script so sánh độ chính xác của việc trích xuất CV từ PDF

So sánh:
1. Ground truth (JSON gốc từ create_cv.py)
2. Extracted data (từ PDF bằng GPT-4o-mini)
"""

import json
import sys
import time
from pathlib import Path
from typing import Dict, Any, List
from openai import OpenAI
import matplotlib.pyplot as plt
import matplotlib
import numpy as np

# Cấu hình matplotlib để hỗ trợ tiếng Việt
matplotlib.rcParams['font.family'] = 'DejaVu Sans'
matplotlib.rcParams['axes.unicode_minus'] = False

from core.config import settings
from app.services.parser_service import ParserService
from app.services.structuring_service import StructuringService
from core.schemas import StructuredData


def calculate_list_similarity(list1: List[str], list2: List[str]) -> float:
    """Tính độ tương đồng giữa 2 danh sách"""
    if not list1 and not list2:
        return 1.0
    if not list1 or not list2:
        return 0.0
    
    # Convert to lowercase sets
    set1 = set([item.lower() for item in list1])
    set2 = set([item.lower() for item in list2])
    
    # Jaccard similarity
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    
    return intersection / union if union > 0 else 0.0


def calculate_field_accuracy(ground_truth: Dict, extracted: Dict, field_path: str) -> Dict[str, Any]:
    """Tính độ chính xác cho một field cụ thể"""
    
    # Lấy giá trị từ nested dict
    def get_nested_value(data, path):
        keys = path.split('.')
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value
    
    gt_value = get_nested_value(ground_truth, field_path)
    ex_value = get_nested_value(extracted, field_path)
    
    # Nếu là list
    if isinstance(gt_value, list) and isinstance(ex_value, list):
        similarity = calculate_list_similarity(gt_value, ex_value)
        return {
            'field': field_path,
            'type': 'list',
            'similarity': similarity,
            'ground_truth_count': len(gt_value),
            'extracted_count': len(ex_value),
            'ground_truth_sample': gt_value[:3] if gt_value else [],
            'extracted_sample': ex_value[:3] if ex_value else []
        }
    
    # Nếu là string
    elif isinstance(gt_value, str) and isinstance(ex_value, str):
        match = 1.0 if gt_value.lower() == ex_value.lower() else 0.0
        return {
            'field': field_path,
            'type': 'string',
            'match': match,
            'ground_truth': gt_value,
            'extracted': ex_value
        }
    
    # Nếu là số
    elif isinstance(gt_value, (int, float)) and isinstance(ex_value, (int, float)):
        # Cho phép sai số 10%
        if gt_value == 0:
            match = 1.0 if ex_value == 0 else 0.0
        else:
            diff = abs(gt_value - ex_value) / abs(gt_value)
            match = 1.0 if diff < 0.1 else 0.0
        
        return {
            'field': field_path,
            'type': 'numeric',
            'match': match,
            'ground_truth': gt_value,
            'extracted': ex_value
        }
    
    # Nếu một trong hai là None
    else:
        both_none = (gt_value is None and ex_value is None)
        return {
            'field': field_path,
            'type': 'other',
            'match': 1.0 if both_none else 0.0,
            'ground_truth': gt_value,
            'extracted': ex_value
        }


def compare_cv_extraction(ground_truth_json: Dict, extracted_json: Dict) -> Dict[str, Any]:
    """So sánh toàn bộ CV extraction"""
    
    fields_to_check = [
        'full_name',
        'email',
        'phone',
        'hard_skills.programming_languages',
        'hard_skills.technologies_frameworks',
        'hard_skills.tools_software',
        'hard_skills.certifications',
        'work_experience.total_years',
        'work_experience.job_titles',
        'work_experience.industries',
        'work_experience.companies',
        'responsibilities_achievements.key_responsibilities',
        'responsibilities_achievements.achievements',
        'soft_skills.communication_teamwork',
        'soft_skills.leadership_management',
        'education_training.degrees',
        'education_training.majors',
        'education_training.universities',
        'additional_factors.languages',
        'additional_factors.availability'
    ]
    
    results = []
    total_score = 0.0
    
    for field in fields_to_check:
        accuracy = calculate_field_accuracy(ground_truth_json, extracted_json, field)
        results.append(accuracy)
        
        # Tính điểm
        if accuracy['type'] == 'list':
            total_score += accuracy['similarity']
        else:
            total_score += accuracy.get('match', 0.0)
    
    overall_accuracy = (total_score / len(fields_to_check)) * 100
    
    return {
        'overall_accuracy': overall_accuracy,
        'total_fields': len(fields_to_check),
        'field_results': results
    }


def plot_overall_accuracy(results_summary: List[Dict], output_dir: Path):
    """Vẽ biểu đồ cột độ chính xác tổng thể của từng CV"""
    if not results_summary:
        return
    
    names = [r['cv_name'] for r in results_summary]
    accuracies = [r['accuracy'] for r in results_summary]
    
    # Rút gọn tên để dễ đọc
    short_names = [name.split()[-1] if len(name.split()) > 2 else name for name in names]
    
    plt.figure(figsize=(12, 6))
    bars = plt.bar(range(len(short_names)), accuracies, color='steelblue', alpha=0.8)
    
    # Thêm giá trị lên đầu mỗi cột
    for i, (bar, acc) in enumerate(zip(bars, accuracies)):
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{acc:.1f}%',
                ha='center', va='bottom', fontsize=9)
    
    # Đường trung bình
    avg_acc = np.mean(accuracies)
    plt.axhline(y=avg_acc, color='red', linestyle='--', linewidth=2, 
                label=f'Trung binh: {avg_acc:.2f}%')
    
    plt.xlabel('CV', fontsize=12, fontweight='bold')
    plt.ylabel('Do chinh xac (%)', fontsize=12, fontweight='bold')
    plt.title('Do chinh xac trich xuat du lieu tu PDF', fontsize=14, fontweight='bold')
    plt.xticks(range(len(short_names)), short_names, rotation=45, ha='right')
    plt.ylim(0, 105)
    plt.legend()
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    
    output_path = output_dir / 'accuracy_overall.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ Đã lưu biểu đồ: {output_path}")


def plot_field_accuracy(results_summary: List[Dict], output_dir: Path):
    """Vẽ biểu đồ heatmap độ chính xác từng trường"""
    if not results_summary:
        return
    
    # Lấy tất cả các trường
    field_names = []
    for result in results_summary:
        for field_result in result['comparison']['field_results']:
            field_name = field_result['field']
            if field_name not in field_names:
                field_names.append(field_name)
    
    # Tạo ma trận độ chính xác
    accuracy_matrix = []
    cv_names = []
    
    for result in results_summary:
        cv_names.append(result['cv_name'].split()[-1])
        row = []
        
        for field_name in field_names:
            # Tìm độ chính xác của trường này
            accuracy = 0.0
            for field_result in result['comparison']['field_results']:
                if field_result['field'] == field_name:
                    if field_result['type'] == 'list':
                        accuracy = field_result['similarity'] * 100
                    else:
                        accuracy = field_result.get('match', 0.0) * 100
                    break
            row.append(accuracy)
        
        accuracy_matrix.append(row)
    
    # Rút gọn tên trường
    short_field_names = [name.split('.')[-1] if '.' in name else name for name in field_names]
    
    # Vẽ heatmap
    fig, ax = plt.subplots(figsize=(16, 8))
    im = ax.imshow(accuracy_matrix, cmap='RdYlGn', aspect='auto', vmin=0, vmax=100)
    
    # Thiết lập ticks
    ax.set_xticks(np.arange(len(short_field_names)))
    ax.set_yticks(np.arange(len(cv_names)))
    ax.set_xticklabels(short_field_names, rotation=90, ha='right', fontsize=8)
    ax.set_yticklabels(cv_names, fontsize=9)
    
    # Thêm giá trị vào mỗi ô
    for i in range(len(cv_names)):
        for j in range(len(short_field_names)):
            text = ax.text(j, i, f'{accuracy_matrix[i][j]:.0f}',
                          ha="center", va="center", color="black", fontsize=6)
    
    ax.set_title('Do chinh xac theo tung truong du lieu', fontsize=14, fontweight='bold')
    ax.set_xlabel('Truong du lieu', fontsize=12, fontweight='bold')
    ax.set_ylabel('CV', fontsize=12, fontweight='bold')
    
    # Colorbar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Do chinh xac (%)', rotation=270, labelpad=20, fontsize=11)
    
    plt.tight_layout()
    output_path = output_dir / 'accuracy_heatmap.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ Đã lưu biểu đồ: {output_path}")


def plot_category_accuracy(results_summary: List[Dict], output_dir: Path):
    """Vẽ biểu đồ độ chính xác theo danh mục"""
    if not results_summary:
        return
    
    categories = {
        'Contact Info': ['full_name', 'email', 'phone'],
        'Hard Skills': ['hard_skills.programming_languages', 'hard_skills.technologies_frameworks', 
                       'hard_skills.tools_software', 'hard_skills.certifications'],
        'Experience': ['work_experience.total_years', 'work_experience.job_titles', 
                      'work_experience.industries', 'work_experience.companies'],
        'Achievements': ['responsibilities_achievements.key_responsibilities', 
                        'responsibilities_achievements.achievements'],
        'Soft Skills': ['soft_skills.communication_teamwork', 'soft_skills.leadership_management'],
        'Education': ['education_training.degrees', 'education_training.majors', 
                     'education_training.universities'],
        'Additional': ['additional_factors.languages', 'additional_factors.availability']
    }
    
    # Tính độ chính xác trung bình cho mỗi category
    category_accuracies = {cat: [] for cat in categories.keys()}
    
    for result in results_summary:
        for cat, fields in categories.items():
            cat_scores = []
            for field_result in result['comparison']['field_results']:
                if field_result['field'] in fields:
                    if field_result['type'] == 'list':
                        cat_scores.append(field_result['similarity'] * 100)
                    else:
                        cat_scores.append(field_result.get('match', 0.0) * 100)
            
            if cat_scores:
                category_accuracies[cat].append(np.mean(cat_scores))
    
    # Vẽ boxplot
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # Boxplot
    data_to_plot = [category_accuracies[cat] for cat in categories.keys()]
    bp = ax1.boxplot(data_to_plot, labels=categories.keys(), patch_artist=True)
    
    for patch in bp['boxes']:
        patch.set_facecolor('lightblue')
        patch.set_alpha(0.7)
    
    ax1.set_ylabel('Do chinh xac (%)', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Danh muc', fontsize=12, fontweight='bold')
    ax1.set_title('Phan bo do chinh xac theo danh muc', fontsize=14, fontweight='bold')
    ax1.grid(axis='y', alpha=0.3)
    ax1.set_xticklabels(categories.keys(), rotation=45, ha='right')
    
    # Bar chart trung bình
    avg_accuracies = [np.mean(category_accuracies[cat]) for cat in categories.keys()]
    bars = ax2.bar(categories.keys(), avg_accuracies, color='steelblue', alpha=0.8)
    
    for bar, acc in zip(bars, avg_accuracies):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{acc:.1f}%',
                ha='center', va='bottom', fontsize=9)
    
    ax2.set_ylabel('Do chinh xac trung binh (%)', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Danh muc', fontsize=12, fontweight='bold')
    ax2.set_title('Do chinh xac trung binh theo danh muc', fontsize=14, fontweight='bold')
    ax2.set_xticklabels(categories.keys(), rotation=45, ha='right')
    ax2.set_ylim(0, 105)
    ax2.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    output_path = output_dir / 'accuracy_by_category.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ Đã lưu biểu đồ: {output_path}")


def main():
    print("="*80)
    print("SO SÁNH ĐỘ CHÍNH XÁC TRÍCH XUẤT CV TỪ PDF")
    print("="*80)
    
    # Khởi tạo services
    print("\n1. Khởi tạo AI services...")
    openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    parser_service = ParserService()
    structuring_service = StructuringService(openai_client)
    
    # Đường dẫn thư mục
    generated_dir = Path("input/cvs/generated")
    
    if not generated_dir.exists():
        print(f"Thư mục {generated_dir} không tồn tại!")
        sys.exit(1)
    
    # Tìm các file PDF và JSON tương ứng
    pdf_files = sorted(generated_dir.glob("cv_*.pdf"))
    
    if not pdf_files:
        print(f"\nKhông tìm thấy file PDF nào trong {generated_dir}")
        print("Vui lòng compile các file .tex thành PDF trước!")
        sys.exit(1)
    
    print(f"\n2. Tìm thấy {len(pdf_files)} file PDF")
    
    # Xử lý từng CV
    results_summary = []
    
    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"\n{'='*80}")
        print(f"Xử lý CV #{i}: {pdf_path.name}")
        print(f"{'='*80}")
        
        # Bắt đầu đo thời gian
        start_time = time.time()
        
        # Tìm file JSON ground truth tương ứng
        json_path = pdf_path.with_suffix('.json')
        
        if not json_path.exists():
            print(f"  ⚠ Không tìm thấy file JSON: {json_path.name}")
            continue
        
        # Load ground truth
        with open(json_path, 'r', encoding='utf-8') as f:
            ground_truth = json.load(f)
        
        print(f"  ✓ Đã load ground truth JSON")
        print(f"  → Tên: {ground_truth['full_name']}")
        
        try:
            # Parse PDF
            print(f"\n  Bước 1: Parse PDF thành text...")
            cv_text = parser_service.parse_file(str(pdf_path))
            print(f"  ✓ Đã parse: {len(cv_text)} ký tự")
            
            # Extract structured data
            print(f"\n  Bước 2: Trích xuất structured data bằng GPT-4o-mini...")
            extracted_json = structuring_service.get_structured_data(
                cv_text,
                StructuredData
            )
            print(f"  ✓ Đã trích xuất")
            
            # So sánh
            print(f"\n  Bước 3: So sánh với ground truth...")
            comparison = compare_cv_extraction(ground_truth, extracted_json)
            
            # Kết thúc đo thời gian
            end_time = time.time()
            processing_time = end_time - start_time
            
            print(f"\n  {'─'*76}")
            print(f"  KẾT QUẢ: Độ chính xác = {comparison['overall_accuracy']:.2f}%")
            print(f"  Thời gian xử lý: {processing_time:.2f} giây")
            print(f"  {'─'*76}")
            
            # Chi tiết một số trường quan trọng
            print(f"\n  Chi tiết một số trường:")
            for result in comparison['field_results'][:5]:
                field_name = result['field']
                if result['type'] == 'list':
                    print(f"    • {field_name}: {result['similarity']*100:.1f}% tương đồng")
                    print(f"      Ground truth: {result['ground_truth_count']} items")
                    print(f"      Extracted: {result['extracted_count']} items")
                elif result['type'] == 'string':
                    match_str = "✓ Khớp" if result['match'] == 1.0 else "✗ Không khớp"
                    print(f"    • {field_name}: {match_str}")
            
            results_summary.append({
                'cv_name': ground_truth['full_name'],
                'pdf_file': pdf_path.name,
                'accuracy': comparison['overall_accuracy'],
                'processing_time': processing_time,
                'comparison': comparison
            })
            
        except Exception as e:
            print(f"  ✗ Lỗi: {str(e)}")
            continue
    
    # Tổng kết
    print(f"\n\n{'='*80}")
    print("TỔNG KẾT")
    print(f"{'='*80}")
    
    if results_summary:
        avg_accuracy = sum(r['accuracy'] for r in results_summary) / len(results_summary)
        avg_time = sum(r['processing_time'] for r in results_summary) / len(results_summary)
        total_time = sum(r['processing_time'] for r in results_summary)
        
        print(f"\nSố CV đã xử lý: {len(results_summary)}")
        print(f"Độ chính xác trung bình: {avg_accuracy:.2f}%")
        print(f"Thời gian xử lý trung bình: {avg_time:.2f} giây/CV")
        print(f"Tổng thời gian xử lý: {total_time:.2f} giây ({total_time/60:.2f} phút)")
        
        print(f"\nChi tiết từng CV:")
        print(f"{'-'*80}")
        print(f"{'Tên CV':30s} | {'Độ chính xác':15s} | {'Thời gian':12s}")
        print(f"{'-'*80}")
        for r in results_summary:
            print(f"{r['cv_name']:30s} | {r['accuracy']:6.2f}%        | {r['processing_time']:6.2f}s")
        print(f"{'-'*80}")
        
        # Lưu kết quả chi tiết
        output_file = Path("cv_extraction_accuracy_report.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results_summary, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Đã lưu báo cáo chi tiết vào: {output_file}")
        
        # Tạo biểu đồ
        print(f"\n{'='*80}")
        print("TẠO BIỂU ĐỒ PHÂN TÍCH")
        print(f"{'='*80}\n")
        
        charts_dir = Path("charts")
        charts_dir.mkdir(exist_ok=True)
        
        print("Đang tạo biểu đồ...")
        plot_overall_accuracy(results_summary, charts_dir)
        plot_field_accuracy(results_summary, charts_dir)
        plot_category_accuracy(results_summary, charts_dir)
        
        print(f"\n✓ Đã lưu tất cả biểu đồ vào thư mục: {charts_dir}")
        print(f"\nCác file biểu đồ:")
        print(f"  1. accuracy_overall.png - Độ chính xác tổng thể")
        print(f"  2. accuracy_heatmap.png - Heatmap chi tiết từng trường")
        print(f"  3. accuracy_by_category.png - Phân tích theo danh mục")
    else:
        print("\nKhông có kết quả nào để hiển thị.")


if __name__ == "__main__":
    main()
