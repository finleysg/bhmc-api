# Django Guidelines

You are an expert in Python, Django, and scalable web application development. You write secure, maintainable, and performant code following Django and Python best practices.

## Python Best Practices
- Follow PEP 8 with 120 character line limit
- Use double quotes for Python strings
- Sort imports with `isort`
- Use f-strings for string formatting
- Use ruff to format and lint any file you touch

## Django Best Practices
- Follow Django's "batteries included" philosophy - use built-in features before third-party packages
- Prioritize security and follow Django's security best practices
- Use Django's ORM effectively and avoid raw SQL unless absolutely necessary
- Use Django signals sparingly and document them well.

## Models
- Add `__str__` methods to all models for a better admin interface
- Use `related_name` for foreign keys when needed
- Define `Meta` class with appropriate options (ordering, verbose_name, etc.)
- Use `blank=True` for optional form fields, `null=True` for optional database fields

## Views
- Always validate and sanitize user input
- Handle exceptions gracefully with try/except blocks
- Use `get_object_or_404` instead of manual exception handling
- Implement proper pagination for list views
- Use ModelViewSet when possible and define @actions for non-crud use cases

## URLs
- Use descriptive URL names for reverse URL lookups
- Always end URL patterns with a trailing slash

## Serializers
- Use existing patterns you find in serializers.py files

## Settings
- Use environment variables in a single `settings.py` file
- Never commit secrets to version control
- Sensitive and per-environment values are managed in /config

## Database
- Use migrations for all database changes
- Optimize queries with `select_related` and `prefetch_related`
- Use database indexes for frequently queried fields
- Avoid N+1 query problems

## Testing
- Only write tests if I explicitly ask you to

## Reference Resources
- [Django Official Documentation](https://docs.djangoproject.com/)
- [Django REST Framework Documentation](https://www.django-rest-framework.org/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [Django Security Best Practices](https://docs.djangoproject.com/en/stable/topics/security/)
- [Django Performance Optimization](https://docs.djangoproject.com/en/stable/topics/performance/)
- [Python PEP 8 Style Guide](https://pep8.org/)
- [Django Testing Documentation](https://docs.djangoproject.com/en/stable/topics/testing/)
