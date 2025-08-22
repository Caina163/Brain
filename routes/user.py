"""
Rotas de Usuários - Brainchild
==============================

Responsável por:
- Perfil pessoal do usuário
- Edição de dados pessoais
- Gerenciamento de usuários (admin)
- Promoção/rebaixamento de usuários
- Configurações da conta
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, make_response
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models.user import User, QuizResult
from models.quiz import Quiz
from utils.decorators import admin_required, check_user_permissions
from utils.helpers import validate_email, validate_password
import re
import csv
from io import StringIO

# Criar blueprint para rotas de usuário
user = Blueprint('user', __name__)


@user.route('/profile')
@login_required
def profile():
    """Perfil do usuário atual"""

    # Estatísticas pessoais (versão simplificada)
    user_stats = {
        'user_type': current_user.user_type,
        'created_at': current_user.created_at,
        'is_approved': current_user.is_approved
    }

    # Atividade recente
    if current_user.user_type == 'student':
        recent_activity = (QuizResult.query
                           .filter_by(user_id=current_user.id)
                           .join(Quiz)
                           .order_by(QuizResult.completed_at.desc())
                           .limit(5)
                           .all())
    else:
        recent_activity = (Quiz.query
                           .filter_by(created_by=current_user.id)
                           .order_by(Quiz.created_at.desc())
                           .limit(5)
                           .all())

    return render_template('user/profile.html',
                           user_stats=user_stats,
                           recent_activity=recent_activity)


@user.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Editar perfil do usuário"""

    if request.method == 'POST':
        db = current_app.extensions['sqlalchemy']
        
        # Obter dados do formulário
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        errors = []

        # Validar campos obrigatórios
        if not all([first_name, last_name, email, current_password]):
            errors.append('Todos os campos obrigatórios devem ser preenchidos.')

        # Verificar senha atual
        if current_password and not current_user.check_password(current_password):
            errors.append('Senha atual incorreta.')

        # Validar nomes
        if first_name and len(first_name) < 2:
            errors.append('Nome deve ter pelo menos 2 caracteres.')
        if last_name and len(last_name) < 2:
            errors.append('Sobrenome deve ter pelo menos 2 caracteres.')

        # Validar email
        if email:
            if not validate_email(email):
                errors.append('Formato de email inválido.')
            elif email != current_user.email:
                # Verificar se email já está em uso
                existing_user = User.query.filter_by(email=email).first()
                if existing_user and existing_user.id != current_user.id:
                    errors.append('Este email já está em uso.')

        # Validar telefone
        if phone and not re.match(r'^[\d\s\-\(\)\+]+$', phone):
            errors.append('Formato de telefone inválido.')

        # Validar nova senha (se fornecida)
        if new_password:
            if new_password != confirm_password:
                errors.append('As senhas não coincidem.')
            else:
                is_valid, password_message = validate_password(new_password)
                if not is_valid:
                    errors.append(password_message)

        # Se há erros, mostrar na página
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('user/edit_profile.html')

        # Atualizar dados
        try:
            current_user.first_name = first_name
            current_user.last_name = last_name
            current_user.email = email
            current_user.phone = phone

            # Atualizar senha se fornecida
            if new_password:
                current_user.password_hash = generate_password_hash(new_password)

            db.session.commit()
            flash('Perfil atualizado com sucesso!', 'success')
            return redirect(url_for('user.profile'))

        except Exception as e:
            db.session.rollback()
            flash('Erro ao atualizar perfil.', 'error')
            print(f"Erro ao atualizar perfil: {e}")

    return render_template('user/edit_profile.html')


@user.route('/manage')
@login_required
@admin_required
def manage_users():
    """Gerenciar usuários (apenas admin)"""

    # Filtros
    user_type_filter = request.args.get('type', 'all')
    status_filter = request.args.get('status', 'all')
    search_query = request.args.get('search', '').strip()

    # Query base
    query = User.query

    # Aplicar filtros
    if user_type_filter != 'all':
        query = query.filter_by(user_type=user_type_filter)

    if status_filter == 'approved':
        query = query.filter_by(is_approved=True)
    elif status_filter == 'pending':
        query = query.filter_by(is_approved=False)

    # Busca por nome, username ou email
    if search_query:
        search_pattern = f'%{search_query}%'
        query = query.filter(
            (User.first_name.ilike(search_pattern)) |
            (User.last_name.ilike(search_pattern)) |
            (User.username.ilike(search_pattern)) |
            (User.email.ilike(search_pattern))
        )

    # Ordenar por data de criação (mais recentes primeiro)
    users = query.order_by(User.created_at.desc()).all()

    # Estatísticas
    stats = {
        'total_users': User.query.count(),
        'admins': User.query.filter_by(user_type='admin').count(),
        'moderators': User.query.filter_by(user_type='moderator').count(),
        'students': User.query.filter_by(user_type='student').count(),
        'pending': User.query.filter_by(is_approved=False).count()
    }

    return render_template('user/manage_users.html',
                           users=users,
                           stats=stats,
                           current_type=user_type_filter,
                           current_status=status_filter,
                           search_query=search_query)


@user.route('/promote/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def promote_user(user_id):
    """Promover usuário (aluno -> moderador)"""
    db = current_app.extensions['sqlalchemy']
    
    target_user = User.query.get_or_404(user_id)

    if target_user.id == current_user.id:
        flash('Você não pode alterar seu próprio tipo de usuário.', 'error')
        return redirect(url_for('user.manage_users'))

    if target_user.user_type == 'student':
        try:
            target_user.user_type = 'moderator'
            db.session.commit()
            flash(f'{target_user.first_name} {target_user.last_name} promovido a moderador!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Erro ao promover usuário.', 'error')
            print(f"Erro ao promover usuário: {e}")
    else:
        flash('Apenas alunos podem ser promovidos a moderadores.', 'warning')

    return redirect(url_for('user.manage_users'))


@user.route('/demote/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def demote_user(user_id):
    """Rebaixar usuário (moderador -> aluno)"""
    db = current_app.extensions['sqlalchemy']
    
    target_user = User.query.get_or_404(user_id)

    if target_user.id == current_user.id:
        flash('Você não pode alterar seu próprio tipo de usuário.', 'error')
        return redirect(url_for('user.manage_users'))

    if target_user.user_type == 'moderator':
        try:
            target_user.user_type = 'student'
            db.session.commit()
            flash(f'{target_user.first_name} {target_user.last_name} rebaixado a aluno!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Erro ao rebaixar usuário.', 'error')
            print(f"Erro ao rebaixar usuário: {e}")
    else:
        flash('Apenas moderadores podem ser rebaixados a alunos.', 'warning')

    return redirect(url_for('user.manage_users'))


@user.route('/toggle_approval/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def toggle_approval(user_id):
    """Alternar aprovação do usuário"""
    db = current_app.extensions['sqlalchemy']
    
    target_user = User.query.get_or_404(user_id)

    if target_user.id == current_user.id:
        flash('Você não pode alterar sua própria aprovação.', 'error')
        return redirect(url_for('user.manage_users'))

    try:
        if target_user.is_approved:
            target_user.is_approved = False
            action = 'desaprovado'
        else:
            target_user.is_approved = True
            action = 'aprovado'

        db.session.commit()
        flash(f'{target_user.first_name} {target_user.last_name} {action} com sucesso!', 'success')

    except Exception as e:
        db.session.rollback()
        flash('Erro ao alterar aprovação.', 'error')
        print(f"Erro ao alterar aprovação: {e}")

    return redirect(url_for('user.manage_users'))


@user.route('/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Excluir usuário (apenas admin)"""
    db = current_app.extensions['sqlalchemy']
    
    target_user = User.query.get_or_404(user_id)

    if target_user.id == current_user.id:
        flash('Você não pode excluir sua própria conta.', 'error')
        return redirect(url_for('user.manage_users'))

    if target_user.user_type == 'admin':
        flash('Não é possível excluir outro administrador.', 'error')
        return redirect(url_for('user.manage_users'))

    user_name = f'{target_user.first_name} {target_user.last_name}'

    try:
        # Excluir usuário
        db.session.delete(target_user)
        db.session.commit()

        flash(f'Usuário {user_name} excluído com sucesso.', 'success')

    except Exception as e:
        db.session.rollback()
        flash('Erro ao excluir usuário.', 'error')
        print(f"Erro ao excluir usuário: {e}")

    return redirect(url_for('user.manage_users'))


@user.route('/export')
@login_required
@admin_required
def export_users():
    """Exportar lista de usuários (CSV)"""

    # Criar CSV em memória
    output = StringIO()
    writer = csv.writer(output)

    # Cabeçalho
    writer.writerow(['ID', 'Username', 'Nome', 'Email', 'Tipo', 'Aprovado', 'Data Criação'])

    # Dados dos usuários
    users = User.query.order_by(User.created_at.desc()).all()
    for user_obj in users:
        user_type_display = {
            'admin': 'Administrador',
            'moderator': 'Moderador', 
            'student': 'Aluno'
        }.get(user_obj.user_type, user_obj.user_type)
        
        writer.writerow([
            user_obj.id,
            user_obj.username,
            f'{user_obj.first_name} {user_obj.last_name}',
            user_obj.email,
            user_type_display,
            'Sim' if user_obj.is_approved else 'Não',
            user_obj.created_at.strftime('%d/%m/%Y %H:%M')
        ])

    # Criar resposta
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = 'attachment; filename=usuarios_brainchild.csv'

    return response
