import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from home.models import Cohort, GameMode, GameStage, TeamUP, Fixture, TeamUPFixture, Round, RoundPlayerStats, TeamUPRound, TeamUPRoundStats, Counties
from users.models import PersonalProfile

User = get_user_model()

class Command(BaseCommand):
    help = 'Generates 20 players and mixed tournament data for testing'

    def handle(self, *args, **options):
        self.stdout.write("Cleaning up existing tournament data...")
        Fixture.objects.all().delete()
        TeamUPFixture.objects.all().delete()
        Round.objects.all().delete()
        TeamUPRound.objects.all().delete()
        TeamUP.objects.all().delete()
        
        self.stdout.write("Generating mock data...")

        # 1. Ensure Counties
        county_names = ['Nairobi', 'Mombasa', 'Kisumu', 'Nakuru', 'Eldoret', 'Kiambu', 'Machakos']
        for name in county_names:
            Counties.objects.get_or_create(name=name)
        counties = list(Counties.objects.all())

        # 2. Ensure Game Modes
        solo_mode, _ = GameMode.objects.get_or_create(
            name='Solo', 
            defaults={'description': 'One vs All', 'amount': 100, 'icon': 'fa-user'}
        )
        team_mode, _ = GameMode.objects.get_or_create(
            name='Team', 
            defaults={'description': 'Squad Battles', 'amount': 400, 'icon': 'fa-users'}
        )
        duo_mode, _ = GameMode.objects.get_or_create(
            name='Duo', 
            defaults={'description': 'Pairs', 'amount': 200, 'icon': 'fa-user-friends'}
        )

        # 3. Ensure Cohort
        now = timezone.now()
        current_cohort, _ = Cohort.objects.get_or_create(
            name='Season 1: Genesis',
            defaults={
                'description': 'The first official season of Elite Tournaments.',
                'start_date': now - timedelta(days=10),
                'end_date': now + timedelta(days=20),
                'closes_at': now + timedelta(days=5),
                'status': 'registration_ongoing',
                'is_open_to_join': True
            }
        )

        # 4. Ensure Game Stages
        stages = []
        for stage_name in ['Qualifiers', 'Semi-Finals', 'Grand Finals']:
            stage, _ = GameStage.objects.get_or_create(
                name=stage_name,
                game_mode=solo_mode,
                defaults={'order': len(stages)}
            )
            stages.append(stage)
        
        team_stages = []
        for stage_name in ['Group Stage', 'Playoffs', 'Finals']:
            stage, _ = GameStage.objects.get_or_create(
                name=stage_name,
                game_mode=team_mode,
                defaults={'order': len(team_stages)}
            )
            team_stages.append(stage)

        # 5. Create 20 Users and include existing ones
        new_players = []
        tags = [
            'ShadowWalker', 'GhostRider', 'EliteSniper', 'CyberPunk', 'NoobMaster69',
            'Slayer99', 'TitanGamer', 'ApexPredator', 'Velocity', 'Xenon',
            'Midnight', 'StormBreaker', 'Rogue', 'Phantom', 'Nexus',
            'Viper', 'Blaze', 'Frost', 'IronClad', 'VoidWalker'
        ]
        
        for i in range(20):
            email = f"player{i+1}@example.com"
            tag = tags[i]
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email,
                    'gamer_tag': tag,
                    'phone_number': f"254700000{i:02d}",
                    'full_name': f"Player {tag}",
                    'county': random.choice(county_names)
                }
            )
            if created:
                user.set_password('password123')
                user.save()
            new_players.append(user)

        # Combine with ALL existing users to ensure the original ones are included
        players = list(User.objects.all())
        
        for user in players:
            # Ensure Profile
            profile, _ = PersonalProfile.objects.get_or_create(user=user)
            current_cohort.participants.add(profile)

        # 6. Create Teams (5 teams of 4)
        teams = []
        for i in range(5):
            team_players = players[i*4 : (i+1)*4]
            team, _ = TeamUP.objects.get_or_create(
                name=f"Team {['Alpha', 'Bravo', 'Charlie', 'Delta', 'Echo'][i]}",
                captain=team_players[0],
                game_mode=team_mode
            )
            team.players.set(team_players)
            current_cohort.teamups.add(team)
            teams.append(team)

        # 7. Generate Solo Fixtures & Results
        for stage in stages:
            # Past Fixture
            fixture = Fixture.objects.create(
                cohort=current_cohort,
                stage=stage,
                match_date=now - timedelta(days=random.randint(1, 5))
            )
            fixture.players.set(random.sample(players, 10))
            
            # Create Round & Stats
            round_inst = Round.objects.create(
                fixture=fixture,
                cohort=current_cohort,
                stage=stage,
                match_date=fixture.match_date
            )
            round_inst.participants.set(fixture.players.all())
            
            for player in fixture.players.all():
                RoundPlayerStats.objects.create(
                    round_instance=round_inst,
                    player=player,
                    rank=random.randint(1, 10),
                    kills=random.randint(0, 15),
                    deaths=random.randint(0, 5),
                    damage=random.randint(500, 3000),
                    xp=random.randint(100, 1000)
                )

            # Future Fixture
            future_fixture = Fixture.objects.create(
                cohort=current_cohort,
                stage=stage,
                match_date=now + timedelta(days=random.randint(1, 5))
            )
            future_fixture.players.set(random.sample(players, 10))

        # 8. Generate Team Fixtures & Results
        for stage in team_stages:
            fixture = TeamUPFixture.objects.create(
                cohort=current_cohort,
                stage=stage,
                match_date=now - timedelta(days=random.randint(1, 5))
            )
            fixture.teamups.set(random.sample(teams, 3))
            
            # Create Team Round & Stats
            team_round = TeamUPRound.objects.create(
                fixture=fixture,
                cohort=current_cohort,
                stage=stage,
                match_date=fixture.match_date
            )
            team_round.teamup.set(fixture.teamups.all())
            
            for team in fixture.teamups.all():
                TeamUPRoundStats.objects.create(
                    round_instance=team_round,
                    team=team,
                    rank=random.randint(1, 3),
                    kills=random.randint(5, 30),
                    deaths=random.randint(5, 20),
                    damage=random.randint(2000, 8000),
                    xp=random.randint(500, 2000)
                )
            
            # Future Team Fixture
            future_team_fixture = TeamUPFixture.objects.create(
                cohort=current_cohort,
                stage=stage,
                match_date=now + timedelta(days=random.randint(1, 5))
            )
            future_team_fixture.teamups.set(random.sample(teams, 3))

        self.stdout.write(self.style.SUCCESS("Mock data generated successfully!"))
