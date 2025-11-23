from django.views.generic import TemplateView, View
from django.shortcuts import render, redirect
from django.contrib import messages
from ..forms import ContactForm


class AboutView(TemplateView):
    template_name = 'about.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any additional context if needed
        return context


class ContactView(View):
    template_name = 'contact.html'
    form_class = ContactForm
    
    def get(self, request):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = self.form_class(request.POST)
        
        if form.is_valid():
            try:
                # Send the email
                form.send_email()
                
                # Add success message
                messages.success(
                    request, 
                    "Thank you for your message! We'll get back to you within 24-48 hours."
                )
                
                # Redirect to avoid re-submission
                return redirect('blog:contact')
                
            except Exception as e:
                # Handle email sending errors
                messages.error(
                    request,
                    "Sorry, there was an error sending your message. Please try again or contact us directly at hello@myblog.com"
                )
        else:
            # Form is not valid
            messages.error(
                request,
                "Please correct the errors below and try again."
            )
        
        return render(request, self.template_name, {'form': form})



class TermsView(TemplateView):
    template_name = 'terms.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class PrivacyView(TemplateView):
    template_name = 'privacy.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context