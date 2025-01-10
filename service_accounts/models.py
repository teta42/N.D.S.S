from django.db import models
from .customuser import CustomUser

class Password_Blocker(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, 
                                primary_key=True, related_name='pb')
    incorrect_password_counter = models.IntegerField(default=0)
    unlock_date = models.DateTimeField(default='2007-09-23 12:53:42.424242')
    next_blocking_for_how_long = models.IntegerField(default=24) # Указание времени для следующей блокировки в часах
    
    class Meta():
        db_table = 'account_block'
        verbose_name = 'Блокировка аккаунта'
        verbose_name_plural = 'Блокировки аккаунтов'
    
    def increase_next_lock(self):
        rev = (24, 168, 720, 876000)
        for i in range(len(rev)):
            if self.next_blocking_for_how_long == rev[i]:
                if i < 3:
                    self.next_blocking_for_how_long = rev[i+1]
                    self.save()
    def __str__(self):
        return self.user.username