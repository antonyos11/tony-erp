from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from .models import Ticket, TicketCategory, TicketComment, KnowledgeBase
from .forms import TicketForm, TicketCommentForm, TicketAssignForm, KnowledgeBaseForm

@login_required
def dashboard(request):
    """Helpdesk dashboard"""
    total_tickets = Ticket.objects.count()
    new_tickets = Ticket.objects.filter(status='new').count()
    open_tickets = Ticket.objects.filter(status='open').count()
    urgent_tickets = Ticket.objects.filter(priority='urgent', status__in=['new', 'open']).count()
    
    my_tickets = Ticket.objects.filter(assigned_to=request.user, status__in=['new', 'open', 'pending']).count()
    
    recent_tickets = Ticket.objects.order_by('-created_at')[:10]
    
    context = {
        'total_tickets': total_tickets,
        'new_tickets': new_tickets,
        'open_tickets': open_tickets,
        'urgent_tickets': urgent_tickets,
        'my_tickets': my_tickets,
        'recent_tickets': recent_tickets,
    }
    return render(request, 'helpdesk/dashboard.html', context)

@login_required
def ticket_list(request):
    """List tickets"""
    tickets = Ticket.objects.all().select_related('category', 'assigned_to', 'customer')
    status = request.GET.get('status')
    priority = request.GET.get('priority')
    if status:
        tickets = tickets.filter(status=status)
    if priority:
        tickets = tickets.filter(priority=priority)
    return render(request, 'helpdesk/ticket_list.html', {'tickets': tickets})

@login_required
def ticket_detail(request, pk):
    """Ticket detail"""
    ticket = get_object_or_404(Ticket.objects.select_related('category', 'assigned_to', 'customer', 'created_by'), pk=pk)
    comments = ticket.comments.filter(is_internal=False) if not request.user.is_staff else ticket.comments.all()
    
    if request.method == 'POST':
        comment_form = TicketCommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.ticket = ticket
            comment.created_by = request.user
            comment.save()
            messages.success(request, 'تم إضافة التعليق')
            return redirect('helpdesk:ticket_detail', pk=pk)
    else:
        comment_form = TicketCommentForm()
    
    context = {
        'ticket': ticket,
        'comments': comments,
        'comment_form': comment_form,
    }
    return render(request, 'helpdesk/ticket_detail.html', context)

@login_required
def ticket_create(request):
    """Create ticket"""
    if request.method == 'POST':
        form = TicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.created_by = request.user
            ticket.ticket_number = f"TKT-{Ticket.objects.count() + 1:06d}"
            if ticket.category and ticket.category.sla_hours:
                ticket.due_date = timezone.now() + timezone.timedelta(hours=ticket.category.sla_hours)
            ticket.save()
            messages.success(request, 'تم إنشاء التذكرة بنجاح')
            return redirect('helpdesk:ticket_detail', pk=ticket.pk)
    else:
        form = TicketForm()
    return render(request, 'helpdesk/ticket_form.html', {'form': form, 'title': 'تذكرة جديدة'})

@login_required
def my_tickets(request):
    """My assigned tickets"""
    tickets = Ticket.objects.filter(assigned_to=request.user).order_by('-created_at')
    return render(request, 'helpdesk/ticket_list.html', {'tickets': tickets, 'title': 'تذاكري'})

@login_required
def knowledge_base(request):
    """Knowledge base articles"""
    articles = KnowledgeBase.objects.filter(is_published=True).order_by('-created_at')
    q = request.GET.get('q')
    if q:
        articles = articles.filter(Q(title__icontains=q) | Q(content__icontains=q))
    return render(request, 'helpdesk/knowledge_base.html', {'articles': articles})

@login_required
def article_detail(request, slug):
    """Article detail"""
    article = get_object_or_404(KnowledgeBase, slug=slug, is_published=True)
    article.view_count += 1
    article.save()
    return render(request, 'helpdesk/article_detail.html', {'article': article})
