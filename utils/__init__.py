"""
Utilitários do Sistema Brainchild
=================================

Este módulo contém funções auxiliares e decoradores:
- decorators: Controle de permissões para rotas
- helpers: Funções auxiliares gerais (upload, formatação, etc.)
"""

from .decorators import (
    admin_required,
    admin_or_moderator_required,
    moderator_required,
    student_required,
    approved_user_required
)

from .helpers import (
    allowed_file,
    save_uploaded_file,
    delete_file,
    format_datetime,
    format_time_ago,
    generate_filename,
    validate_quiz_data,
    validate_question_data,
    calculate_quiz_score
)

# Lista de todas as funções disponíveis para import
__all__ = [
    # Decoradores de permissão
    'admin_required',
    'admin_or_moderator_required',
    'moderator_required',
    'student_required',
    'approved_user_required',

    # Funções auxiliares
    'allowed_file',
    'save_uploaded_file',
    'delete_file',
    'format_datetime',
    'format_time_ago',
    'generate_filename',
    'validate_quiz_data',
    'validate_question_data',
    'calculate_quiz_score'
]

# Versão do módulo
__version__ = '1.0.0'