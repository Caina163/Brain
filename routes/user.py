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

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from models.user import User, QuizResult
from models.quiz import Quiz
from utils.decorators import admin_required, check_user_permissions
from utils.helpers import validate_email, validate_password
import re

# Criar blueprint para rotas de usuário
user = Blueprint('user', __name__)


@user.route('/profile')
@login_required
def profile():
    """Perfil do usuário atual"""

    # Estatísticas pessoais
    user_stats = current_user.get_quiz_stats()

    # Atividade recente
    if current_user.is_student:
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
                current_user.set_password(new_password)

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

    target_user = User.query.get_or_404(user_id)

    if target_user.id == current_user.id:
        flash('Você não pode alterar seu próprio tipo de usuário.', 'error')
        return redirect(url_for('user.manage_users'))

    if target_user.is_student:
        try:
            target_user.promote_to_moderator()
            db.session.commit()
            flash(f'{target_user.full_name} promovido a moderador!', 'success')
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

    target_user = User.query.get_or_404(user_id)

    if target_user.id == current_user.id:
        flash('Você não pode alterar seu próprio tipo de usuário.', 'error')
        return redirect(url_for('user.manage_users'))

    if target_user.is_moderator:
        try:
            target_user.demote_to_student()
            db.session.commit()
            flash(f'{target_user.full_name} rebaixado a aluno!', 'success')
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
        flash(f'{target_user.full_name} {action} com sucesso!', 'success')

    except Exception as e:
        db.session.rollback()
        flash('Erro ao alterar aprovação.', 'error')
        print(f"Erro ao alterar aprovação: {e}")

    return redirect(url_for('user.manage_users'))


@user.route('/view/<int:user_id>')
@login_required
def view_user(user_id):
    """Visualizar perfil de outro usuário"""

    target_user = User.query.get_or_404(user_id)

    # Verificar permissão
    if not check_user_permissions(target_user, 'view'):
        flash('Você não tem permissão para ver este perfil.', 'error')
        return redirect(url_for('dashboard.index'))

    # Estatísticas do usuário
    user_stats = target_user.get_quiz_stats()

    # Atividade recente (limitada se não for admin)
    if target_user.is_student:
        recent_activity = (QuizResult.query
                           .filter_by(user_id=target_user.id)
                           .join(Quiz)
                           .order_by(QuizResult.completed_at.desc())
                           .limit(5 if current_user.is_admin else 3)
                           .all())
    else:
        recent_activity = (Quiz.query
                           .filter_by(created_by=target_user.id)
                           .order_by(Quiz.created_at.desc())
                           .limit(5 if current_user.is_admin else 3)
                           .all())

    return render_template('user/view_user.html',
                           target_user=target_user,
                           user_stats=user_stats,
                           recent_activity=recent_activity,
                           can_edit=check_user_permissions(target_user, 'edit'))


@user.route('/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Excluir usuário (apenas admin)"""

    target_user = User.query.get_or_404(user_id)

    if target_user.id == current_user.id:
        flash('Você não pode excluir sua própria conta.', 'error')
        return redirect(url_for('user.manage_users'))

    if target_user.is_admin:
        flash('Não é possível excluir outro administrador.', 'error')
        return redirect(url_for('user.manage_users'))

    user_name = target_user.full_name

    try:
        # Excluir usuário (CASCADE vai excluir quizzes e resultados relacionados)
        db.session.delete(target_user)
        db.session.commit()

        flash(f'Usuário {user_name} excluído com sucesso.', 'success')

    except Exception as e:
        db.session.rollback()
        flash('Erro ao excluir usuário.', 'error')
        print(f"Erro ao excluir usuário: {e}")

    return redirect(url_for('user.manage_users'))


@user.route('/bulk_action', methods=['POST'])
@login_required
@admin_required
def bulk_action():
    """Ações em lote para usuários"""

    action = request.form.get('action')
    user_ids = request.form.getlist('user_ids')

    if not user_ids:
        flash('Nenhum usuário selecionado.', 'warning')
        return redirect(url_for('user.manage_users'))

    try:
        user_ids = [int(uid) for uid in user_ids if uid != str(current_user.id)]
        users = User.query.filter(User.id.in_(user_ids)).all()

        count = 0

        if action == 'approve':
            for user_obj in users:
                if not user_obj.is_approved:
                    user_obj.is_approved = True
                    count += 1
            flash(f'{count} usuário(s) aprovado(s)!', 'success')

        elif action == 'disapprove':
            for user_obj in users:
                if user_obj.is_approved and not user_obj.is_admin:
                    user_obj.is_approved = False
                    count += 1
            flash(f'{count} usuário(s) desaprovado(s)!', 'success')

        elif action == 'promote':
            for user_obj in users:
                if user_obj.is_student:
                    user_obj.promote_to_moderator()
                    count += 1
            flash(f'{count} usuário(s) promovido(s) a moderador!', 'success')

        elif action == 'demote':
            for user_obj in users:
                if user_obj.is_moderator:
                    user_obj.demote_to_student()
                    count += 1
            flash(f'{count} usuário(s) rebaixado(s) a aluno!', 'success')

        elif action == 'delete':
            for user_obj in users:
                if not user_obj.is_admin:
                    db.session.delete(user_obj)
                    count += 1
            flash(f'{count} usuário(s) excluído(s)!', 'success')

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        flash('Erro ao executar ação em lote.', 'error')
        print(f"Erro na ação em lote: {e}")

    return redirect(url_for('user.manage_users'))


@user.route('/export')
@login_required
@admin_required
def export_users():
    """Exportar lista de usuários (CSV)"""

    from flask import make_response
    import csv
    from io import StringIO

    # Criar CSV em memória
    output = StringIO()
    writer = csv.writer(output)

    # Cabeçalho
    writer.writerow(['ID', 'Username', 'Nome', 'Email', 'Tipo', 'Aprovado', 'Data Criação'])

    # Dados dos usuários
    users = User.query.order_by(User.created_at.desc()).all()
    for user_obj in users:
        writer.writerow([
            user_obj.id,
            user_obj.username,
            user_obj.full_name,
            user_obj.email,
            user_obj.get_user_type_display(),
            'Sim' if user_obj.is_approved else 'Não',
            user_obj.created_at.strftime('%d/%m/%Y %H:%M')
        ])

    # Criar resposta
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = 'attachment; filename=usuarios_brainchild.csv'

    return response


@user.route('/api/user_stats/<int:user_id>')
@login_required
def api_user_stats(user_id):
    """API para estatísticas do usuário"""

    target_user = User.query.get_or_404(user_id)

    # Verificar permissão
    if not check_user_permissions(target_user, 'view'):
        return jsonify({'error': 'Sem permissão'}), 403

    stats = target_user.get_quiz_stats()

    return jsonify({
        'user_type': target_user.user_type,
        'stats': stats,
        'full_name': target_user.full_name,
        'created_at': target_user.created_at.isoformat()
    })


# Context processor para dados de usuário
@user.context_processor
def inject_user_data():
    """Disponibiliza dados úteis para templates de usuário"""
    data = {}

    if current_user.is_authenticated and current_user.is_admin:
        data['pending_users_count'] = User.query.filter_by(is_approved=False).count()
        data['total_users_count'] = User.query.count()

    return data