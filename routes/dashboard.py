"""
Rotas de Dashboard - Brainchild
===============================

Responsável por:
- Dashboard principal com redirecionamento inteligente
- Dashboard do administrador (controle total)
- Dashboard do moderador (criação e edição de quizzes)
- Dashboard do aluno (jogar quizzes)
- Estatísticas e resumos personalizados
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, desc
from app import db
from models.user import User, QuizResult
from models.quiz import Quiz
from models.question import Question
from utils.decorators import admin_required, admin_or_moderator_required, approved_user_required
from utils.helpers import format_datetime, format_time_ago
from datetime import datetime, timedelta

# Criar blueprint para rotas de dashboard
dashboard = Blueprint('dashboard', __name__)


@dashboard.route('/')
@login_required
@approved_user_required
def index():
    """Dashboard principal - redireciona baseado no tipo de usuário"""

    if current_user.is_admin:
        return redirect(url_for('dashboard.admin'))
    elif current_user.is_moderator:
        return redirect(url_for('dashboard.moderator'))
    elif current_user.is_student:
        return redirect(url_for('dashboard.student'))
    else:
        flash('Tipo de usuário não reconhecido.', 'error')
        return redirect(url_for('auth.logout'))


@dashboard.route('/admin')
@login_required
@admin_required
def admin():
    """Dashboard do administrador"""

    # Estatísticas gerais do sistema
    stats = {
        'total_users': User.query.count(),
        'pending_users': User.query.filter_by(is_approved=False).count(),
        'admins': User.query.filter_by(user_type='admin').count(),
        'moderators': User.query.filter_by(user_type='moderator').count(),
        'students': User.query.filter_by(user_type='student').count(),
        'total_quizzes': Quiz.query.count(),
        'active_quizzes': Quiz.query.filter_by(is_active=True, is_deleted=False).count(),
        'archived_quizzes': Quiz.query.filter_by(is_archived=True).count(),
        'deleted_quizzes': Quiz.query.filter_by(is_deleted=True).count(),
        'total_questions': Question.query.count(),
        'total_quiz_plays': QuizResult.query.count()
    }

    # Usuários recentes (últimos 10)
    recent_users = User.query.order_by(desc(User.created_at)).limit(10).all()

    # Quizzes populares (mais jogados)
    popular_quizzes = (db.session.query(Quiz, func.count(QuizResult.id).label('play_count'))
                       .join(QuizResult, Quiz.id == QuizResult.quiz_id)
                       .group_by(Quiz.id)
                       .order_by(desc('play_count'))
                       .limit(5)
                       .all())

    # Usuários pendentes de aprovação
    pending_users = User.query.filter_by(is_approved=False).order_by(User.created_at.desc()).limit(5).all()

    # Atividade recente (últimos resultados)
    recent_activity = (QuizResult.query
                       .join(User, QuizResult.user_id == User.id)
                       .join(Quiz, QuizResult.quiz_id == Quiz.id)
                       .order_by(desc(QuizResult.completed_at))
                       .limit(10)
                       .all())

    # Estatísticas por período (últimos 30 dias)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_stats = {
        'new_users': User.query.filter(User.created_at >= thirty_days_ago).count(),
        'new_quizzes': Quiz.query.filter(Quiz.created_at >= thirty_days_ago).count(),
        'quiz_plays': QuizResult.query.filter(QuizResult.completed_at >= thirty_days_ago).count()
    }

    return render_template('dashboard/admin.html',
                           stats=stats,
                           recent_users=recent_users,
                           popular_quizzes=popular_quizzes,
                           pending_users=pending_users,
                           recent_activity=recent_activity,
                           recent_stats=recent_stats)


@dashboard.route('/moderator')
@login_required
@admin_or_moderator_required
def moderator():
    """Dashboard do moderador"""

    # Estatísticas pessoais
    my_quizzes = Quiz.query.filter_by(created_by=current_user.id).all()

    stats = {
        'my_quizzes_count': len(my_quizzes),
        'active_quizzes': len([q for q in my_quizzes if q.is_active and not q.is_deleted]),
        'total_plays': sum(len(q.results) for q in my_quizzes),
        'total_questions': sum(len(q.questions) for q in my_quizzes),
        'pending_users': User.query.filter_by(is_approved=False).count() if current_user.can_approve_users else 0
    }

    # Meus quizzes mais populares
    my_popular_quizzes = sorted(my_quizzes, key=lambda q: len(q.results), reverse=True)[:5]

    # Quizzes recentes que criei
    recent_quizzes = Quiz.query.filter_by(created_by=current_user.id).order_by(desc(Quiz.created_at)).limit(5).all()

    # Resultados recentes dos meus quizzes
    recent_results = (QuizResult.query
                      .join(Quiz, QuizResult.quiz_id == Quiz.id)
                      .filter(Quiz.created_by == current_user.id)
                      .join(User, QuizResult.user_id == User.id)
                      .order_by(desc(QuizResult.completed_at))
                      .limit(10)
                      .all())

    # Estatísticas gerais do sistema (se for moderador)
    system_stats = None
    if current_user.is_moderator:
        system_stats = {
            'total_users': User.query.filter_by(is_approved=True).count(),
            'total_quizzes': Quiz.query.filter_by(is_active=True, is_deleted=False).count(),
            'total_plays': QuizResult.query.count()
        }

    return render_template('dashboard/moderator.html',
                           stats=stats,
                           my_popular_quizzes=my_popular_quizzes,
                           recent_quizzes=recent_quizzes,
                           recent_results=recent_results,
                           system_stats=system_stats)


@dashboard.route('/student')
@login_required
@approved_user_required
def student():
    """Dashboard do aluno"""

    # Estatísticas pessoais
    my_results = QuizResult.query.filter_by(user_id=current_user.id).all()

    if my_results:
        total_score = sum(r.score for r in my_results)
        total_questions = sum(r.total_questions for r in my_results)
        average_percentage = (total_score / total_questions * 100) if total_questions > 0 else 0
        best_score = max(r.percentage_score for r in my_results)

        stats = {
            'quizzes_played': len(my_results),
            'total_questions_answered': total_questions,
            'average_score': round(average_percentage, 1),
            'best_score': round(best_score, 1),
            'total_time_spent': sum(r.time_spent or 0 for r in my_results)
        }
    else:
        stats = {
            'quizzes_played': 0,
            'total_questions_answered': 0,
            'average_score': 0,
            'best_score': 0,
            'total_time_spent': 0
        }

    # Quizzes disponíveis para jogar
    available_quizzes = (Quiz.query
                         .filter_by(is_active=True, is_archived=False, is_deleted=False)
                         .order_by(desc(Quiz.created_at))
                         .limit(10)
                         .all())

    # Meus resultados recentes
    recent_results = (QuizResult.query
                      .filter_by(user_id=current_user.id)
                      .join(Quiz, QuizResult.quiz_id == Quiz.id)
                      .order_by(desc(QuizResult.completed_at))
                      .limit(5)
                      .all())

    # Quizzes recomendados (baseado em dificuldade e performance)
    recommended_quizzes = []
    if my_results:
        # Recomendar quizzes com dificuldade similar ao desempenho do usuário
        avg_performance = stats['average_score']
        if avg_performance >= 80:
            # Usuário bom - recomendar quizzes mais difíceis
            recommended_quizzes = (Quiz.query
                                   .filter_by(is_active=True, is_archived=False, is_deleted=False)
                                   .outerjoin(QuizResult)
                                   .group_by(Quiz.id)
                                   .having(func.avg(QuizResult.score * 100 / QuizResult.total_questions) < 70)
                                   .limit(3)
                                   .all())
        elif avg_performance >= 60:
            # Usuário médio - recomendar quizzes médios
            recommended_quizzes = available_quizzes[:3]
        else:
            # Usuário iniciante - recomendar quizzes mais fáceis
            recommended_quizzes = (Quiz.query
                                   .filter_by(is_active=True, is_archived=False, is_deleted=False)
                                   .outerjoin(QuizResult)
                                   .group_by(Quiz.id)
                                   .having(func.avg(QuizResult.score * 100 / QuizResult.total_questions) > 70)
                                   .limit(3)
                                   .all())
    else:
        # Usuário novo - recomendar quizzes populares
        recommended_quizzes = available_quizzes[:3]

    # Ranking pessoal (posição entre todos os alunos)
    if my_results:
        user_avg = stats['average_score']
        better_users = (db.session.query(func.count(User.id))
                        .join(QuizResult)
                        .group_by(User.id)
                        .having(func.avg(QuizResult.score * 100 / QuizResult.total_questions) > user_avg)
                        .count())
        total_students = User.query.filter_by(user_type='student', is_approved=True).count()
        ranking_position = better_users + 1
    else:
        ranking_position = None
        total_students = User.query.filter_by(user_type='student', is_approved=True).count()

    return render_template('dashboard/student.html',
                           stats=stats,
                           available_quizzes=available_quizzes,
                           recent_results=recent_results,
                           recommended_quizzes=recommended_quizzes,
                           ranking_position=ranking_position,
                           total_students=total_students)


@dashboard.route('/stats')
@login_required
@approved_user_required
def stats():
    """Página de estatísticas detalhadas"""

    # Redirecionar baseado no tipo de usuário
    if current_user.is_admin:
        return redirect(url_for('dashboard.admin_stats'))
    elif current_user.is_moderator:
        return redirect(url_for('dashboard.moderator_stats'))
    else:
        return redirect(url_for('dashboard.student_stats'))


@dashboard.route('/admin/stats')
@login_required
@admin_required
def admin_stats():
    """Estatísticas detalhadas para administrador"""

    # Estatísticas por período
    periods = ['7', '30', '90', '365']
    period_stats = {}

    for days in periods:
        start_date = datetime.utcnow() - timedelta(days=int(days))
        period_stats[days] = {
            'new_users': User.query.filter(User.created_at >= start_date).count(),
            'new_quizzes': Quiz.query.filter(Quiz.created_at >= start_date).count(),
            'quiz_plays': QuizResult.query.filter(QuizResult.completed_at >= start_date).count()
        }

    # Top performers
    top_students = (db.session.query(
        User,
        func.count(QuizResult.id).label('total_plays'),
        func.avg(QuizResult.score * 100 / QuizResult.total_questions).label('avg_score')
    )
                    .join(QuizResult)
                    .filter(User.user_type == 'student')
                    .group_by(User.id)
                    .order_by(desc('avg_score'))
                    .limit(10)
                    .all())

    # Top quiz creators
    top_creators = (db.session.query(
        User,
        func.count(Quiz.id).label('quiz_count'),
        func.sum(func.coalesce(func.count(QuizResult.id), 0)).label('total_plays')
    )
                    .join(Quiz, User.id == Quiz.created_by)
                    .outerjoin(QuizResult, Quiz.id == QuizResult.quiz_id)
                    .group_by(User.id)
                    .order_by(desc('quiz_count'))
                    .limit(10)
                    .all())

    return render_template('dashboard/admin_stats.html',
                           period_stats=period_stats,
                           top_students=top_students,
                           top_creators=top_creators)


@dashboard.route('/api/chart-data/<chart_type>')
@login_required
@approved_user_required
def chart_data(chart_type):
    """API para dados de gráficos"""

    if chart_type == 'user_growth':
        # Crescimento de usuários nos últimos 30 dias
        data = []
        for i in range(30):
            date = datetime.utcnow() - timedelta(days=i)
            count = User.query.filter(User.created_at <= date).count()
            data.append({
                'date': date.strftime('%Y-%m-%d'),
                'count': count
            })
        return jsonify(data)

    elif chart_type == 'quiz_plays':
        # Jogos de quiz nos últimos 7 dias
        data = []
        for i in range(7):
            date = datetime.utcnow() - timedelta(days=i)
            start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)

            count = QuizResult.query.filter(
                QuizResult.completed_at >= start_of_day,
                QuizResult.completed_at < end_of_day
            ).count()

            data.append({
                'date': date.strftime('%Y-%m-%d'),
                'count': count
            })
        return jsonify(data)

    elif chart_type == 'user_types':
        # Distribuição de tipos de usuário
        data = [
            {'type': 'Administradores', 'count': User.query.filter_by(user_type='admin').count()},
            {'type': 'Moderadores', 'count': User.query.filter_by(user_type='moderator').count()},
            {'type': 'Alunos', 'count': User.query.filter_by(user_type='student').count()}
        ]
        return jsonify(data)

    return jsonify({'error': 'Tipo de gráfico não encontrado'}), 404


@dashboard.route('/search')
@login_required
@approved_user_required
def search():
    """Busca global no sistema"""

    query = request.args.get('q', '').strip()
    if not query:
        return redirect(url_for('dashboard.index'))

    # Buscar quizzes
    quizzes = Quiz.query.filter(
        Quiz.title.contains(query),
        Quiz.is_active == True,
        Quiz.is_deleted == False
    ).limit(10).all()

    # Buscar usuários (apenas para admin)
    users = []
    if current_user.is_admin:
        users = User.query.filter(
            (User.username.contains(query)) |
            (User.first_name.contains(query)) |
            (User.last_name.contains(query))
        ).limit(10).all()

    return render_template('dashboard/search_results.html',
                           query=query,
                           quizzes=quizzes,
                           users=users)