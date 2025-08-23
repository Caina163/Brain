@dashboard.route('/admin')
@login_required
@admin_required
def admin():
    """Dashboard do administrador - DEBUG VERSION"""
    
    # Teste 1: Estatísticas básicas sem campos problemáticos
    stats = {
        'total_users': User.query.count(),
        'total_quizzes': Quiz.query.count(),
        'active_quizzes': Quiz.query.filter(Quiz.status == 'active').count(),
        'pending_users': User.query.filter_by(is_approved=False).count(),
        'admins': 0,
        'moderators': 0, 
        'students': 0,
        'archived_quizzes': 0,
        'deleted_quizzes': 0,
        'total_questions': 0,
        'total_quiz_plays': 0
    }
    
    # Teste 2: Dados mínimos
    recent_users = []
    popular_quizzes = []
    pending_users = []
    recent_activity = []
    recent_stats = {'new_users': 0, 'new_quizzes': 0, 'quiz_plays': 0}
    
    return render_template('dashboard/admin.html',
                           stats=stats,
                           recent_users=recent_users,
                           popular_quizzes=popular_quizzes,
                           pending_users=pending_users,
                           recent_activity=recent_activity,
                           recent_stats=recent_stats)
