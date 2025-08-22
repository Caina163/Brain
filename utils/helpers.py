"""
Funções Auxiliares - Brainchild
===============================

Funções utilitárias para:
- Upload e gerenciamento de arquivos
- Validação de dados
- Formatação de datas e texto
- Cálculos de pontuação
"""

import os
import uuid
import re
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from PIL import Image
from flask import current_app, flash

# Extensões de arquivo permitidas
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_IMAGE_SIZE = (1920, 1080)  # Redimensionar imagens grandes


def allowed_file(filename):
    """
    Verifica se o arquivo tem extensão permitida

    Args:
        filename (str): Nome do arquivo

    Returns:
        bool: True se permitido, False caso contrário
    """
    if not filename:
        return False

    return ('.' in filename and
            filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS)


def generate_filename(original_filename):
    """
    Gera nome único para arquivo mantendo a extensão

    Args:
        original_filename (str): Nome original do arquivo

    Returns:
        str: Nome único gerado
    """
    if not original_filename:
        return None

    # Obter extensão
    if '.' in original_filename:
        extension = original_filename.rsplit('.', 1)[1].lower()
    else:
        extension = 'jpg'  # Default

    # Gerar nome único
    unique_name = str(uuid.uuid4())
    return f"{unique_name}.{extension}"


def save_uploaded_file(file, upload_folder=None):
    """
    Salva arquivo enviado com validações e otimizações

    Args:
        file: Arquivo do FormData
        upload_folder (str): Pasta de destino (opcional)

    Returns:
        str: Nome do arquivo salvo ou None se erro
    """
    if not file or file.filename == '':
        return None

    if not allowed_file(file.filename):
        flash('Tipo de arquivo não permitido. Use: PNG, JPG, JPEG, GIF, WEBP', 'error')
        return None

    # Definir pasta de upload
    if not upload_folder:
        upload_folder = current_app.config['UPLOAD_FOLDER']

    # Criar pasta se não existir
    os.makedirs(upload_folder, exist_ok=True)

    # Gerar nome único
    filename = generate_filename(file.filename)
    filepath = os.path.join(upload_folder, filename)

    try:
        # Salvar arquivo temporariamente
        file.save(filepath)

        # Otimizar imagem
        optimize_image(filepath)

        return filename

    except Exception as e:
        print(f"Erro ao salvar arquivo: {e}")
        # Remover arquivo se houver erro
        if os.path.exists(filepath):
            os.remove(filepath)
        return None


def optimize_image(filepath):
    """
    Otimiza imagem redimensionando e comprimindo

    Args:
        filepath (str): Caminho do arquivo
    """
    try:
        with Image.open(filepath) as img:
            # Converter para RGB se necessário
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')

            # Redimensionar se muito grande
            if img.size[0] > MAX_IMAGE_SIZE[0] or img.size[1] > MAX_IMAGE_SIZE[1]:
                img.thumbnail(MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)

            # Salvar com compressão
            img.save(filepath, 'JPEG', quality=85, optimize=True)

    except Exception as e:
        print(f"Erro ao otimizar imagem: {e}")


def delete_file(filename, upload_folder=None):
    """
    Remove arquivo do sistema

    Args:
        filename (str): Nome do arquivo
        upload_folder (str): Pasta onde está o arquivo

    Returns:
        bool: True se removido, False caso contrário
    """
    if not filename:
        return False

    if not upload_folder:
        upload_folder = current_app.config['UPLOAD_FOLDER']

    filepath = os.path.join(upload_folder, filename)

    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
    except Exception as e:
        print(f"Erro ao remover arquivo: {e}")

    return False


def format_datetime(dt, format_type='full'):
    """
    Formata data/hora para exibição

    Args:
        dt (datetime): Data/hora
        format_type (str): 'full', 'date', 'time', 'short'

    Returns:
        str: Data formatada
    """
    if not dt:
        return 'Data não informada'

    if format_type == 'full':
        return dt.strftime('%d/%m/%Y às %H:%M')
    elif format_type == 'date':
        return dt.strftime('%d/%m/%Y')
    elif format_type == 'time':
        return dt.strftime('%H:%M')
    elif format_type == 'short':
        return dt.strftime('%d/%m às %H:%M')
    else:
        return str(dt)


def format_time_ago(dt):
    """
    Formata tempo relativo (ex: "há 2 horas")

    Args:
        dt (datetime): Data/hora

    Returns:
        str: Tempo relativo formatado
    """
    if not dt:
        return 'Data desconhecida'

    now = datetime.utcnow()
    diff = now - dt

    if diff.days > 30:
        return format_datetime(dt, 'date')
    elif diff.days > 0:
        return f"há {diff.days} dia{'s' if diff.days > 1 else ''}"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"há {hours} hora{'s' if hours > 1 else ''}"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"há {minutes} minuto{'s' if minutes > 1 else ''}"
    else:
        return "agora mesmo"


def validate_email(email):
    """
    Valida formato de email

    Args:
        email (str): Email para validar

    Returns:
        bool: True se válido, False caso contrário
    """
    if not email:
        return False

    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password(password):
    """
    Valida força da senha

    Args:
        password (str): Senha para validar

    Returns:
        tuple: (bool, str) - (é_válida, mensagem)
    """
    if not password:
        return False, "Senha é obrigatória"

    if len(password) < 6:
        return False, "Senha deve ter pelo menos 6 caracteres"

    if len(password) > 128:
        return False, "Senha muito longa"

    # Verificações opcionais para senha mais forte
    has_letter = any(c.isalpha() for c in password)
    has_number = any(c.isdigit() for c in password)

    if not has_letter:
        return False, "Senha deve conter pelo menos uma letra"

    if not has_number:
        return False, "Senha deve conter pelo menos um número"

    return True, "Senha válida"


def validate_quiz_data(data):
    """
    Valida dados de criação/edição de quiz

    Args:
        data (dict): Dados do quiz

    Returns:
        tuple: (bool, list) - (é_válido, lista_de_erros)
    """
    errors = []

    # Título
    title = data.get('title', '').strip()
    if not title:
        errors.append("Título é obrigatório")
    elif len(title) < 3:
        errors.append("Título deve ter pelo menos 3 caracteres")
    elif len(title) > 200:
        errors.append("Título muito longo (máximo 200 caracteres)")

    # Descrição (opcional)
    description = data.get('description', '').strip()
    if description and len(description) > 1000:
        errors.append("Descrição muito longa (máximo 1000 caracteres)")

    # Tempo limite (opcional)
    time_limit = data.get('time_limit')
    if time_limit is not None:
        try:
            time_limit = int(time_limit)
            if time_limit < 1 or time_limit > 180:
                errors.append("Tempo limite deve estar entre 1 e 180 minutos")
        except (ValueError, TypeError):
            errors.append("Tempo limite deve ser um número válido")

    return len(errors) == 0, errors


def validate_question_data(data):
    """
    Valida dados de criação/edição de questão

    Args:
        data (dict): Dados da questão

    Returns:
        tuple: (bool, list) - (é_válido, lista_de_erros)
    """
    errors = []

    # Texto da questão
    question_text = data.get('question_text', '').strip()
    if not question_text:
        errors.append("Texto da questão é obrigatório")
    elif len(question_text) < 10:
        errors.append("Questão deve ter pelo menos 10 caracteres")
    elif len(question_text) > 2000:
        errors.append("Questão muito longa (máximo 2000 caracteres)")

    # Resposta correta
    correct_answer = data.get('correct_answer', '').strip()
    if not correct_answer:
        errors.append("Resposta correta é obrigatória")
    elif len(correct_answer) > 500:
        errors.append("Resposta correta muito longa (máximo 500 caracteres)")

    # Verificar se há pelo menos uma alternativa incorreta
    option_a = data.get('option_a', '').strip()
    option_b = data.get('option_b', '').strip()
    option_c = data.get('option_c', '').strip()

    if not any([option_a, option_b, option_c]):
        errors.append("Pelo menos uma alternativa incorreta é obrigatória")

    # Validar tamanho das alternativas
    for option, name in [(option_a, 'A'), (option_b, 'B'), (option_c, 'C')]:
        if option and len(option) > 500:
            errors.append(f"Alternativa {name} muito longa (máximo 500 caracteres)")

    return len(errors) == 0, errors


def calculate_quiz_score(user_answers, correct_answers):
    """
    Calcula pontuação do quiz

    Args:
        user_answers (list): Respostas do usuário
        correct_answers (list): Respostas corretas

    Returns:
        dict: Resultado com pontuação e estatísticas
    """
    if not user_answers or not correct_answers:
        return {
            'score': 0,
            'total_questions': 0,
            'percentage': 0,
            'correct_answers': [],
            'incorrect_answers': []
        }

    total_questions = len(correct_answers)
    correct_count = 0
    correct_indices = []
    incorrect_indices = []

    for i, (user_answer, correct_answer) in enumerate(zip(user_answers, correct_answers)):
        if user_answer and user_answer.strip().lower() == correct_answer.strip().lower():
            correct_count += 1
            correct_indices.append(i)
        else:
            incorrect_indices.append(i)

    percentage = (correct_count / total_questions) * 100 if total_questions > 0 else 0

    return {
        'score': correct_count,
        'total_questions': total_questions,
        'percentage': round(percentage, 1),
        'correct_answers': correct_indices,
        'incorrect_answers': incorrect_indices
    }


def sanitize_filename(filename):
    """
    Sanitiza nome de arquivo removendo caracteres perigosos

    Args:
        filename (str): Nome do arquivo

    Returns:
        str: Nome sanitizado
    """
    if not filename:
        return 'arquivo'

    # Usar secure_filename do Werkzeug
    safe_name = secure_filename(filename)

    # Se ficou vazio, usar nome padrão
    if not safe_name:
        return 'arquivo'

    return safe_name


def truncate_text(text, max_length=100, suffix='...'):
    """
    Trunca texto mantendo palavras inteiras

    Args:
        text (str): Texto para truncar
        max_length (int): Comprimento máximo
        suffix (str): Sufixo para texto truncado

    Returns:
        str: Texto truncado
    """
    if not text or len(text) <= max_length:
        return text or ''

    # Truncar no último espaço antes do limite
    truncated = text[:max_length].rsplit(' ', 1)[0]
    return truncated + suffix


def get_file_size(filepath):
    """
    Obtém tamanho do arquivo em formato legível

    Args:
        filepath (str): Caminho do arquivo

    Returns:
        str: Tamanho formatado (ex: "1.5 MB")
    """
    try:
        size_bytes = os.path.getsize(filepath)

        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
    except:
        return "Tamanho desconhecido"


def generate_quiz_slug(title):
    """
    Gera slug amigável para URL baseado no título do quiz

    Args:
        title (str): Título do quiz

    Returns:
        str: Slug gerado
    """
    if not title:
        return 'quiz'

    # Converter para minúsculas e remover acentos
    slug = title.lower()
    slug = re.sub(r'[áàâãä]', 'a', slug)
    slug = re.sub(r'[éèêë]', 'e', slug)
    slug = re.sub(r'[íìîï]', 'i', slug)
    slug = re.sub(r'[óòôõö]', 'o', slug)
    slug = re.sub(r'[úùûü]', 'u', slug)
    slug = re.sub(r'[ç]', 'c', slug)

    # Remover caracteres especiais e substituir espaços por hífens
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    slug = slug.strip('-')

    return slug or 'quiz'