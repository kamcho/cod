from django.db import models

class Counties(models.Model):
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name


class Cohort(models.Model):
    status_choices = [
        ('upcoming', 'Upcoming'),
        ('running', 'Running'),
        ('registration_ongoing', 'Registration Ongoing'),
        ('completed', 'Completed'),
    ]
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    closes_at = models.DateTimeField()
    status = models.CharField(max_length=20, default='upcoming', choices=status_choices)
    is_open_to_join = models.BooleanField(default=True)
    participants = models.ManyToManyField('users.PersonalProfile',blank=True,related_name='cohort_participants')
    teamups = models.ManyToManyField('home.TeamUP',blank=True, related_name='cohort_teamups')
    def __str__(self):
        return self.name

class GameMode(models.Model):
    NAME_CHOICES = [
        ('Solo', 'Solo'),
        ('Team', 'Team'),
        ('Duo', 'Duo'),
        ('Squad', 'Squad'),
    ]
    name = models.CharField(max_length=50, choices=NAME_CHOICES, unique=True)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    max_players = models.PositiveIntegerField(default=4)
    icon = models.CharField(max_length=50, blank=True, help_text="CSS class for icon (e.g. fa-users)")

    def __str__(self):
        return self.get_name_display()

class TeamUP(models.Model):
    name = models.CharField(max_length=100)
    captain = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='captain')
    game_mode = models.ForeignKey('home.GameMode', on_delete=models.CASCADE, related_name='teamups')
    players = models.ManyToManyField('users.User', related_name='teamups')
    
    def get_payment_status(self, cohort):
        """Returns a list of dictionaries with player payment status for a cohort."""
        status = []
        for player in self.players.all():
            has_paid = MPesaTransaction.objects.filter(
                user=player,
                cohort=cohort,
                game_mode=self.game_mode,
                team=self,
                status='SUCCESS'
            ).exists()
            status.append({'player': player, 'paid': has_paid})
        return status

    def is_ready(self, cohort):
        """Checks if the squad is full and all members have paid for the cohort."""
        if self.players.count() < self.game_mode.max_players:
            return False
        
        # Check if all players have at least one successful payment for this specific cohort and team
        for player in self.players.all():
            paid = MPesaTransaction.objects.filter(
                user=player,
                cohort=cohort,
                game_mode=self.game_mode,
                team=self,
                status='SUCCESS'
            ).exists()
            if not paid:
                return False
        return True

    def __str__(self):
        return self.name    


class GameStage(models.Model):
    cohort = models.ForeignKey('home.Cohort',default=1, on_delete=models.CASCADE, related_name='cohort_stages')
    name = models.CharField(max_length=100)
    game_mode = models.ForeignKey('home.GameMode', on_delete=models.CASCADE, related_name='stages')
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0, help_text="Order of the stage in a competition")
    is_final = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name

class StageParticipants(models.Model):
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name='participants_cohort')
    stage = models.ForeignKey(GameStage, on_delete=models.CASCADE, related_name='stage_participants')
    participant = models.ForeignKey('users.PersonalProfile', null=True, blank=True, on_delete=models.CASCADE, related_name='participant_stage')    
    teamup = models.ForeignKey('home.TeamUP', null=True, blank=True, on_delete=models.CASCADE, related_name='teamup_stage')


class Fixture(models.Model):
    cohort = models.ForeignKey(Cohort,null=True, blank=True, on_delete=models.CASCADE, related_name='fixture_cohort')
    stage = models.ForeignKey(GameStage, on_delete=models.CASCADE, related_name='fixtures')
    players = models.ManyToManyField('users.User', related_name='fixtures')
    match_date = models.DateTimeField()

class TeamUPFixture(models.Model):
    cohort = models.ForeignKey(Cohort,null=True, blank=True, on_delete=models.CASCADE, related_name='teamup_fixture_cohort')
    stage = models.ForeignKey(GameStage, on_delete=models.CASCADE, related_name='teamup_fixtures')
    teamups = models.ManyToManyField('home.TeamUP', related_name='teamup_fixtures')
    match_date = models.DateTimeField()


class Round(models.Model):
    fixture = models.OneToOneField(Fixture, on_delete=models.SET_NULL, null=True, blank=True, related_name='round_result')
    cohort = models.ForeignKey(Cohort,null=True, blank=True, on_delete=models.CASCADE, related_name='cohort')
    stage = models.ForeignKey(GameStage, on_delete=models.CASCADE, related_name='rounds')
    participants = models.ManyToManyField('users.User', related_name='rounds')
    match_date = models.DateTimeField()


    def __str__(self):
        return f"{self.stage.name} - {self.match_date.strftime('%Y-%m-%d %H:%M')}" 

class RoundPlayerStats(models.Model):
    round_instance = models.ForeignKey(Round, on_delete=models.CASCADE, related_name='teamup_stats')
    player = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='player_stats')
    rank = models.IntegerField()
    kills = models.IntegerField()
    deaths = models.IntegerField()
    damage = models.IntegerField(default=0, null=True, blank=True)
    time_alive = models.CharField(max_length=20, null=True, blank=True, help_text="e.g. 12:45")
    xp= models.IntegerField()
    
    def __str__(self):
        return f"{self.player.gamer_tag} - {self.round_instance.stage.name} - {self.rank}"
    

class TeamUPRound(models.Model):
    fixture = models.OneToOneField(TeamUPFixture, on_delete=models.SET_NULL, null=True, blank=True, related_name='round_result')
    cohort = models.ForeignKey(Cohort,null=True, blank=True, on_delete=models.CASCADE, related_name='teamup_cohort')
    stage = models.ForeignKey(GameStage, on_delete=models.CASCADE, related_name='teamup_rounds')
    teamup = models.ManyToManyField('home.TeamUP', related_name='teamup_rounds')
    match_date = models.DateTimeField()


    def __str__(self):
        return f"{self.id} - {self.match_date.strftime('%Y-%m-%d %H:%M')}" 

class TeamUPRoundStats(models.Model):
    round_instance = models.ForeignKey(TeamUPRound, on_delete=models.CASCADE, related_name='team_stats')
    team = models.ForeignKey('home.TeamUP', on_delete=models.CASCADE, related_name='team_round_stats')
    rank = models.IntegerField()
    kills = models.IntegerField(default=0) # Aggregated from players
    deaths = models.IntegerField(default=0)
    damage = models.IntegerField(default=0, null=True, blank=True)
    xp = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.team.name} - Rank {self.rank}"

class TeamUPPlayerRoundStats(models.Model):
    round_instance = models.ForeignKey(TeamUPRound, on_delete=models.CASCADE, related_name='player_team_stats')
    team = models.ForeignKey('home.TeamUP', on_delete=models.CASCADE, related_name='player_match_stats')
    player = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='team_player_stats')
    kills = models.IntegerField(default=0)
    deaths = models.IntegerField(default=0)
    damage = models.IntegerField(default=0)
    xp = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.player.gamer_tag} in {self.team.name} - {self.kills} Kills"

class TeamUPInvite(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ACCEPTED', 'Accepted'),
        ('DECLINED', 'Declined'),
    ]
    inviter = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='sent_invites')
    invitee = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='received_invites')
    team = models.ForeignKey(TeamUP, on_delete=models.CASCADE, related_name='invites')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Invite: {self.inviter} -> {self.invitee} for {self.team.name}"

class Notification(models.Model):
    TYPE_CHOICES = [
        ('FIXTURE', 'New Fixture'),
        ('RESULT', 'Match Result'),
        ('INVITE', 'Squad Invite'),
        ('SYSTEM', 'System Alert'),
    ]
    
    recipient = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='notifications')
    actor = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_notifications')
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    link = models.CharField(max_length=255, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

class MPesaTransaction(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
    ]
    merchant_request_id = models.CharField(max_length=100, unique=True)
    checkout_request_id = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    phone_number = models.CharField(max_length=15)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='mpesa_transactions')
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name='mpesa_transactions')
    game_mode = models.ForeignKey(GameMode, on_delete=models.CASCADE, related_name='mpesa_transactions', null=True, blank=True)
    team = models.ForeignKey(TeamUP, on_delete=models.SET_NULL, null=True, blank=True, related_name='mpesa_transactions')
    result_code = models.IntegerField(null=True, blank=True)
    result_description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment {self.checkout_request_id} - {self.status}"

class FreeAgent(models.Model):
    user = models.OneToOneField('users.User', on_delete=models.CASCADE, related_name='free_agent_profile')
    game_modes = models.ManyToManyField(GameMode, related_name='free_agents')
    message = models.TextField(help_text="Describe your skills, playstyle, and what you're looking for.")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Free Agent: {self.user.gamer_tag}"

class SquadRecruitment(models.Model):
    team = models.ForeignKey(TeamUP, on_delete=models.CASCADE, related_name='recruitment_posts')
    slots_open = models.PositiveIntegerField(default=1)
    requirements = models.TextField(blank=True, help_text="e.g. 'Must have MIC', 'Rank 50+', etc.")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Recruiting for {self.team.name} ({self.slots_open} slots)"

class JoinRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    player = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='join_requests')
    team = models.ForeignKey(TeamUP, on_delete=models.CASCADE, related_name='join_requests')
    message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Request: {self.player.gamer_tag} to {self.team.name} ({self.status})"




