"""
Decoradores de Permissão - Brainchild
=====================================

Decoradores para controlar acesso às rotas baseado no tipo de usuário:
- admin_required: Apenas administradores
- admin_or_moderator_required: Administradores ou moderadores
- moderator_required: Apenas moderadores
- student_required: Apenas alunos
- approved_user_required: Usuários aprovados (qualquer tipo)
"""

from functools import wraps
from flask import redirect, url_for, flash, abort, request
from flask_login import current_user


def admin_required(f):
    """
    Decorador que exige usuário administrador
    Uso: @admin_required
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Você precisa fazer login para acessar esta página.', 'warning')
            return redirect(url_for('auth.login', next=request.url))

        if not current_user.is_approved:
            flash('Sua conta ainda não foi aprovada.', 'warning')
            return redirect(url_for('dashboard.index'))

        if not current_user.is_admin:
            flash('Acesso negado. Esta área é restrita a administradores.', 'danger')
            return redirect(url_for('dashboard.index'))

        return f(*args, **kwargs)

    return decorated_function


def admin_or_moderator_required(f):
    """
    Decorador que exige usuário administrador ou moderador
    Uso: @admin_or_moderator_required
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Você precisa fazer login para acessar esta página.', 'warning')
            return redirect(url_for('auth.login', next=request.url))

        if not current_user.is_approved:
            flash('Sua conta ainda não foi aprovada.', 'warning')
            return redirect(url_for('dashboard.index'))

        if not (current_user.is_admin or current_user.is_moderator):
            flash('Acesso negado. Esta área é restrita a administradores e moderadores.', 'danger')
            return redirect(url_for('dashboard.index'))

        return f(*args, **kwargs)

    return decorated_function


def moderator_required(f):
    """
    Decorador que exige usuário moderador (não inclui admin)
    Uso: @moderator_required
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Você precisa fazer login para acessar esta página.', 'warning')
            return redirect(url_for('auth.login', next=request.url))

        if not current_user.is_approved:
            flash('Sua conta ainda não foi aprovada.', 'warning')
            return redirect(url_for('dashboard.index'))

        if not current_user.is_moderator:
            flash('Acesso negado. Esta área é restrita a moderadores.', 'danger')
            return redirect(url_for('dashboard.index'))

        return f(*args, **kwargs)

    return decorated_function


def student_required(f):
    """
    Decorador que exige usuário aluno
    Uso: @student_required
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Você precisa fazer login para acessar esta página.', 'warning')
            return redirect(url_for('auth.login', next=request.url))

        if not current_user.is_approved:
            flash('Sua conta ainda não foi aprovada.', 'warning')
            return redirect(url_for('dashboard.index'))

        if not current_user.is_student:
            flash('Acesso negado. Esta área é restrita a alunos.', 'danger')
            return redirect(url_for('dashboard.index'))

        return f(*args, **kwargs)

    return decorated_function


def approved_user_required(f):
    """
    Decorador que exige usuário aprovado (qualquer tipo)
    Uso: @approved_user_required
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Você precisa fazer login para acessar esta página.', 'warning')
            return redirect(url_for('auth.login', next=request.url))

        if not current_user.is_approved:
            flash('Sua conta ainda não foi aprovada. Aguarde a aprovação de um administrador.', 'warning')
            return redirect(url_for('auth.login'))

        return f(*args, **kwargs)

    return decorated_function


def quiz_owner_or_admin_required(f):
    """
    Decorador que exige que o usuário seja o criador do quiz ou administrador
    Uso: @quiz_owner_or_admin_required
    Nota: A função decorada deve receber quiz_id como parâmetro
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Você precisa fazer login para acessar esta página.', 'warning')
            return redirect(url_for('auth.login', next=request.url))

        if not current_user.is_approved:
            flash('Sua conta ainda não foi aprovada.', 'warning')
            return redirect(url_for('dashboard.index'))

        # Verificar se há quiz_id nos argumentos
        quiz_id = kwargs.get('quiz_id') or kwargs.get('id')
        if not quiz_id:
            abort(404)

        # Importar aqui para evitar import circular
        from models.quiz import Quiz
        quiz = Quiz.query.get_or_404(quiz_id)

        # Verificar se é o criador do quiz ou admin
        if not (current_user.is_admin or quiz.created_by == current_user.id):
            flash('Você não tem permissão para editar este quiz.', 'danger')
            return redirect(url_for('dashboard.index'))

        return f(*args, **kwargs)

    return decorated_function


def api_key_required(f):
    """
    Decorador para proteger APIs (uso futuro)
    Uso: @api_key_required
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return {'error': 'API key required'}, 401

        # Verificar API key (implementar lógica conforme necessário)
        # Por enquanto, aceitar qualquer chave para desenvolvimento

        return f(*args, **kwargs)

    return decorated_function


def rate_limit_required(limit=100, window=3600):
    """
    Decorador para rate limiting (uso futuro)
    Uso: @rate_limit_required(limit=50, window=3600)
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Implementar rate limiting conforme necessário
            # Por enquanto, permitir todas as requisições
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def check_quiz_permissions(quiz, action='view'):
    """
    Função auxiliar para verificar permissões específicas em quizzes

    Args:
        quiz: Objeto Quiz
        action: 'view', 'edit', 'delete', 'archive'

    Returns:
        bool: True se tem permissão, False caso contrário
    """
    if not current_user.is_authenticated or not current_user.is_approved:
        return False

    if action == 'view':
        # Qualquer usuário aprovado pode ver quizzes ativos
        return quiz.can_be_played()

    elif action == 'edit':
        # Criador do quiz ou admin pode editar
        return (current_user.is_admin or
                quiz.created_by == current_user.id) and quiz.can_be_edited()

    elif action in ['delete', 'archive']:
        # Apenas admin pode arquivar/excluir qualquer quiz
        # Criador pode arquivar próprios quizzes
        if current_user.is_admin:
            return True
        return quiz.created_by == current_user.id

    return False


def check_user_permissions(target_user, action='view'):
    """
    Função auxiliar para verificar permissões sobre outros usuários

    Args:
        target_user: Objeto User alvo
        action: 'view', 'edit', 'promote', 'approve'

    Returns:
        bool: True se tem permissão, False caso contrário
    """
    if not current_user.is_authenticated or not current_user.is_approved:
        return False

    if action == 'view':
        # Usuário pode ver próprio perfil, admin pode ver todos
        return current_user.id == target_user.id or current_user.is_admin

    elif action == 'edit':
        # Usuário pode editar próprio perfil, admin pode editar todos
        return current_user.id == target_user.id or current_user.is_admin

    elif action == 'promote':
        # Apenas admin pode promover/rebaixar usuários
        return current_user.is_admin

    elif action == 'approve':
        # Admin e moderadores podem aprovar cadastros
        return current_user.is_admin or current_user.is_moderator

    return False