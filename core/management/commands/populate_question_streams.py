from django.core.management.base import BaseCommand
from assessment.models import Question
from stream_domain_mapping.models import StreamDomainMapping
from education_level.models import EducationLevel


class Command(BaseCommand):
    help = "Populate stream field for questions based on their mapped domains and StreamDomainMapping."

    def handle(self, *args, **options):
        # Get higher_secondary education level
        try:
            higher_secondary = EducationLevel.objects.get(level_code="higher_secondary")
        except EducationLevel.DoesNotExist:
            self.stdout.write(self.style.ERROR("EducationLevel 'higher_secondary' not found."))
            return

        # Get all questions with higher_secondary education_level
        questions = Question.objects.filter(education_level=higher_secondary, is_active=True)

        updated_count = 0
        for question in questions:
            # Get all streams for the question's domains
            stream_scores = {}
            for domain in question.mapped_domains.all():
                mappings = StreamDomainMapping.objects.filter(
                    domain=domain,
                    is_active=True,
                    stream__education_level=higher_secondary
                )
                for mapping in mappings:
                    stream = mapping.stream
                    score = mapping.weight_score
                    if stream in stream_scores:
                        stream_scores[stream] += score
                    else:
                        stream_scores[stream] = score

            if stream_scores:
                # Pick the stream with the highest total score
                best_stream = max(stream_scores, key=stream_scores.get)
                question.stream = best_stream
                question.save()
                updated_count += 1
                self.stdout.write(f"Updated question {question.id} with stream {best_stream.stream_name}")
            else:
                self.stdout.write(f"No stream found for question {question.id}")

        self.stdout.write(self.style.SUCCESS(f"Updated {updated_count} questions with streams."))
