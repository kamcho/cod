from django.contrib import admin
from .models import Cohort, GameMode, TeamUP, GameStage, StageParticipants, Round, RoundPlayerStats, TeamUPRound, TeamUPRoundStats, Fixture, TeamUPFixture, TeamUPPlayerRoundStats, Notification, MPesaTransaction, TeamUPInvite, FreeAgent, SquadRecruitment, JoinRequest

# Register your models here.
admin.site.register(Cohort)
admin.site.register(GameMode)
admin.site.register(TeamUP)
admin.site.register(GameStage)
admin.site.register(StageParticipants)
admin.site.register(Round)
admin.site.register(RoundPlayerStats)
admin.site.register(TeamUPRound)
admin.site.register(TeamUPRoundStats)
admin.site.register(TeamUPPlayerRoundStats)
admin.site.register(Notification)
admin.site.register(Fixture)
admin.site.register(TeamUPFixture)
admin.site.register(MPesaTransaction)
admin.site.register(TeamUPInvite)
admin.site.register(FreeAgent)
admin.site.register(SquadRecruitment)
admin.site.register(JoinRequest)