import os

def load_lines_from_file(filepath):
    """Lấy nội dung từng dòng từ file text, bỏ qua dòng trống."""
    if not os.path.exists(filepath):
        return []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    # Loại bỏ khoảng trắng 2 đầu và bỏ qua dòng trống
    return [line.strip() for line in lines if line.strip()]
