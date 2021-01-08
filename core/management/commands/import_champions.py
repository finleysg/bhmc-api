import csv

from django.core.management.base import BaseCommand

from register.models import Player
from core.models import MajorChampion


class Command(BaseCommand):
    help = 'Import major champions from the given file'

    def add_arguments(self, parser):
        parser.add_argument('file')

    def handle(self, *args, **options):
        filename = options['file']
        count = 0
        errors = 0

        with open(filename, newline='') as csvfile:
            reader = csv.reader(csvfile, delimiter=',', quotechar='"')
            # TODO: detect header
            # next(reader)
            for row in reader:
                season = int(row[0])
                event_name = row[1]
                flight = row[2]
                gross_net = row[3]
                champion = row[4]
                score = row[5]

                try:
                    player = None
                    first_last = champion.split(" ")
                    players = Player.objects.filter(last_name=first_last[1])
                    if len(players) == 1:
                        player = players[0]
                    elif len(players) > 1:
                        for p in players:
                            if p.first_name.startswith(first_last[0]) or p.first_name == first_last[0]:
                                player = p

                    if player is None:
                        print("could not find player for " + champion)
                        errors += 1
                    else:
                        new_champion = MajorChampion.objects.create(season=season,
                                                                    event_name=event_name,
                                                                    flight=gross_net + " " + flight,
                                                                    player=player,
                                                                    score=score)
                        new_champion.save()
                        count += 1
                except Exception as ex:
                    print('failure ' + str(ex))
                    errors += 1

        self.stdout.write(self.style.SUCCESS('Successfully imported %s champions with %s errors' % (count, errors)))
