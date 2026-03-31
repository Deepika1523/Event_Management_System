from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from .models import Event, Activity

@login_required
def event_activities_pdf(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    activities = Activity.objects.filter(event=event).prefetch_related('coordinators__user')
    
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Header
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(50, height - 80, event.event)
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, height - 110, f"Date: {event.date_of_event}")
    pdf.drawString(50, height - 130, f"Venue: {event.venue}")
    pdf.drawString(50, height - 150, f"Total Activities: {activities.count()}")
    
    y = height - 180
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, y, "Activities")
    y -= 30
    
    # Activities
    pdf.setFont("Helvetica-Bold", 12)
    for i, activity in enumerate(activities, 1):
        pdf.drawString(50, y, f"{i}. {activity.name}")
        y -= 20
        pdf.setFont("Helvetica", 11)
        pdf.drawString(70, y, f"Time: {activity.start_time} - {activity.end_time or ''}")
        y -= 15
        pdf.drawString(70, y, f"Fee: {activity.registration_fee}")
        y -= 15
        coordinators = ', '.join([c.user.username for c in activity.coordinators.all()]) or 'None'
        pdf.drawString(70, y, f"Coordinators: {coordinators}")
        y -= 20
        pdf.setFont("Helvetica-Bold", 12)
        
        if y < 100:
            pdf.showPage()
            y = height - 60
    
    pdf.save()
    buffer.seek(0)
    
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="event_{event.id}_activities.pdf"'
    return response

