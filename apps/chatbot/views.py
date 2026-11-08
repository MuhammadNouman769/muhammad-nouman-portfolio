from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .knowledge import answer_question


@require_POST
def answer(request):
    question = request.POST.get('question', '').strip()
    if len(question) > 500:
        return JsonResponse({'error': 'Please keep your question under 500 characters.'}, status=400)
    if not question:
        return JsonResponse({'error': 'Please enter a question.'}, status=400)
    if request.POST.get('website'):
        return JsonResponse({'error': 'Unable to process this request.'}, status=400)
    return JsonResponse(answer_question(question))
