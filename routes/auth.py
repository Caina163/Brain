"""
Rotas de Autenticação - Brainchild
==================================

Responsável por:
- Login de usuários
- Registro com aprovação pendente
- Logout
- Sistema de aprovação/reprovação de cadastros
- Gerenciamento de cadastros pendentes
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from models.user import User
from utils.decorators import admin_or_moderator_required, admin_required
from utils.helpers import validate_email, validate_password
import re

# Criar blueprint para rotas de autenticação
auth = Blueprint('auth', __name__)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login"""
    # Se já está logado, redirecionar para dashboard
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        # Validações básicas
        if not username or not password:
            flash('Por favor, preencha todos os campos.', 'error')
            return render_template('auth/login.html')

        # Buscar usuário (pode ser username ou email)
        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()

        if user and user.check_password(password):
            if not user.is_approved:
                flash('Sua conta ainda não foi aprovada. Aguarde a aprovação de um administrador.', 'warning')
                return render_template('auth/login.html')

            # Login bem-sucedido
            login_user(user, remember=remember)

            # Redirecionar para página solicitada ou dashboard
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                flash(f'Bem-vindo de volta, {user.full_name}!', 'success')
                return redirect(next_page)

            flash(f'Bem-vindo, {user.full_name}!', 'success')
            return redirect(url_for('dashboard.index'))
        else:
            flash('Usuário ou senha incorretos.', 'error')

    return render_template('auth/login.html')


@auth.route('/register', methods=['GET', 'POST'])
def register():
    """Página de registro"""
    # Se já está logado, redirecionar para dashboard
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        # Obter dados do formulário
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        phone = request.form.get('phone', '').strip()

        # Lista de erros
        errors = []

        # Validar campos obrigatórios
        if not all([username, email, password, confirm_password, first_name, last_name]):
            errors.append('Todos os campos obrigatórios devem ser preenchidos.')

        # Validar username
        if username:
            if len(username) < 3:
                errors.append('Nome de usuário deve ter pelo menos 3 caracteres.')
            elif len(username) > 80:
                errors.append('Nome de usuário muito longo.')
            elif not re.match(r'^[a-zA-Z0-9_]+$', username):
                errors.append('Nome de usuário deve conter apenas letras, números e underscore.')
            elif User.query.filter_by(username=username).first():
                errors.append('Este nome de usuário já está em uso.')

        # Validar email
        if email:
            if not validate_email(email):
                errors.append('Formato de email inválido.')
            elif User.query.filter_by(email=email).first():
                errors.append('Este email já está cadastrado.')

        # Validar senha
        if password:
            is_valid, password_message = validate_password(password)
            if not is_valid:
                errors.append(password_message)

        # Confirmar senha
        if password != confirm_password:
            errors.append('As senhas não coincidem.')

        # Validar nomes
        if first_name and len(first_name) < 2:
            errors.append('Nome deve ter pelo menos 2 caracteres.')
        if last_name and len(last_name) < 2:
            errors.append('Sobrenome deve ter pelo menos 2 caracteres.')

        # Validar telefone (opcional)
        if phone and not re.match(r'^[\d\s\-\(\)\+]+$', phone):
            errors.append('Formato de telefone inválido.')

        # Se há erros, mostrar na página
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('auth/register.html',
                                   username=username, email=email,
                                   first_name=first_name, last_name=last_name,
                                   phone=phone)

        # Criar novo usuário (pendente de aprovação)
        try:
            from flask import current_app
            
            new_user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                user_type='student',  # Por padrão, novos usuários são alunos
                is_approved=False  # Precisa de aprovação
            )

            current_app.extensions['sqlalchemy'].session.add(new_user)
            current_app.extensions['sqlalchemy'].session.commit()

            flash('Cadastro realizado com sucesso! Aguarde a aprovação de um administrador.', 'success')
            return redirect(url_for('auth.login'))

        except Exception as e:
            current_app.extensions['sqlalchemy'].session.rollback()
            flash('Erro interno. Tente novamente mais tarde.', 'error')
            print(f"Erro no registro: {e}")

    return render_template('auth/register.html')


@auth.route('/logout')
@login_required
def logout():
    """Logout do usuário"""
    user_name = current_user.full_name
    logout_user()
    flash(f'Até logo, {user_name}!', 'info')
    return redirect(url_for('auth.login'))


@auth.route('/pending')
@login_required
@admin_or_moderator_required
def pending_users():
    """Lista de usuários pendentes de aprovação"""
    pending = User.query.filter_by(is_approved=False).order_by(User.created_at.desc()).all()
    return render_template('auth/pending.html', pending_users=pending)


@auth.route('/approve_user/<int:user_id>', methods=['POST'])
@login_required
@admin_or_moderator_required
def approve_user(user_id):
    """Aprovar usuário pendente"""
    user = User.query.get_or_404(user_id)

    if user.is_approved:
        flash('Este usuário já foi aprovado.', 'warning')
        return redirect(url_for('auth.pending_users'))

    # Aprovar usuário
    user.is_approved = True
    current_app.extensions['sqlalchemy'].session.commit()

    flash(f'Usuário {user.full_name} aprovado com sucesso!', 'success')
    return redirect(url_for('auth.pending_users'))


@auth.route('/reject_user/<int:user_id>', methods=['POST'])
@login_required
@admin_or_moderator_required
def reject_user(user_id):
    """Rejeitar e remover usuário pendente"""
    user = User.query.get_or_404(user_id)

    if user.is_approved:
        flash('Não é possível rejeitar usuário já aprovado.', 'error')
        return redirect(url_for('auth.pending_users'))

    user_name = user.full_name

    try:
        current_app.extensions['sqlalchemy'].session.delete(user)
        current_app.extensions['sqlalchemy'].session.commit()
        flash(f'Cadastro de {user_name} rejeitado e removido.', 'info')
    except Exception as e:
        current_app.extensions['sqlalchemy'].session.rollback()
        flash('Erro ao rejeitar usuário.', 'error')
        print(f"Erro ao rejeitar usuário: {e}")

    return redirect(url_for('auth.pending_users'))


@auth.route('/bulk_approve', methods=['POST'])
@login_required
@admin_or_moderator_required
def bulk_approve():
    """Aprovar múltiplos usuários de uma vez"""
    user_ids = request.form.getlist('user_ids')

    if not user_ids:
        flash('Nenhum usuário selecionado.', 'warning')
        return redirect(url_for('auth.pending_users'))

    try:
        # Converter para inteiros
        user_ids = [int(uid) for uid in user_ids]

        # Aprovar usuários selecionados
        users = User.query.filter(User.id.in_(user_ids), User.is_approved == False).all()

        approved_count = 0
        for user in users:
            user.is_approved = True
            approved_count += 1

        current_app.extensions['sqlalchemy'].session.commit()

        flash(f'{approved_count} usuário(s) aprovado(s) com sucesso!', 'success')

    except Exception as e:
        current_app.extensions['sqlalchemy'].session.rollback()
        flash('Erro ao aprovar usuários em lote.', 'error')
        print(f"Erro na aprovação em lote: {e}")

    return redirect(url_for('auth.pending_users'))


@auth.route('/check_username', methods=['POST'])
def check_username():
    """API para verificar disponibilidade do username"""
    username = request.json.get('username', '').strip()

    if not username:
        return jsonify({'available': False, 'message': 'Username não informado'})

    if len(username) < 3:
        return jsonify({'available': False, 'message': 'Username muito curto'})

    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return jsonify({'available': False, 'message': 'Username inválido'})

    exists = User.query.filter_by(username=username).first() is not None

    return jsonify({
        'available': not exists,
        'message': 'Username já está em uso' if exists else 'Username disponível'
    })


@auth.route('/check_email', methods=['POST'])
def check_email():
    """API para verificar disponibilidade do email"""
    email = request.json.get('email', '').strip().lower()

    if not email:
        return jsonify({'available': False, 'message': 'Email não informado'})

    if not validate_email(email):
        return jsonify({'available': False, 'message': 'Formato de email inválido'})

    exists = User.query.filter_by(email=email).first() is not None

    return jsonify({
        'available': not exists,
        'message': 'Email já está cadastrado' if exists else 'Email disponível'
    })


@auth.route('/resend_approval')
@login_required
def resend_approval():
    """Reenviar solicitação de aprovação (placeholder)"""
    if current_user.is_approved:
        flash('Sua conta já está aprovada.', 'info')
        return redirect(url_for('dashboard.index'))

    # Aqui poderia implementar envio de email para admins
    flash('Solicitação de aprovação reenviada. Aguarde o contato dos administradores.', 'info')
    return redirect(url_for('auth.login'))


# Filtros personalizados para templates
@auth.app_template_filter('pending_count')
def pending_count_filter(user_type=None):
    """Filtro para contar usuários pendentes"""
    query = User.query.filter_by(is_approved=False)
    if user_type:
        query = query.filter_by(user_type=user_type)
    return query.count()


# Context processor para disponibilizar dados em templates de auth
@auth.context_processor
def inject_auth_data():
    """Disponibiliza dados úteis para templates de autenticação"""
    data = {}

    # Se usuário logado tem permissão para ver pendentes
    if current_user.is_authenticated and (current_user.is_admin or current_user.is_moderator):
        data['pending_users_count'] = User.query.filter_by(is_approved=False).count()

    return data
