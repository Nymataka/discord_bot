import discord
from discord.ext import commands
from discord.ui import Button, View
from random import sample as random
import os

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
list_channels = ['table', '1', '2', '3', '4', 'pass']  # список всех каналов
list_roles = ("1", "2", "3", "4", "pass")  # список всех ролей
roles = []  # список участвующих ролей
ready = 0  # количество готовых игроков
turns = None  # список участвующих ролей
turn_now = None  # текущий ход


@bot.event
async def on_ready():  # запуск программы
    for channels in list_channels:  # очистка каналов
        group = discord.utils.get(bot.get_all_channels(), name=f'{channels}')
        await group.purge(limit=100)
    channel = discord.utils.get(bot.get_all_channels(), name='table')
    roles = tuple(discord.utils.get(channel.guild.roles, name=n) for n in list_roles)
    users = bot.get_all_members()
    [await user.remove_roles(*roles) for user in users if user.bot is False]  # забрать у всех роли
    view = RolesView(channel)
    await channel.send('Выбери роль', view=view)  # отправка кнопок с выбором роли


class RolesView(View):  # представление роли
    def __init__(self, ctx):
        super().__init__(timeout=5)
        self.ctx = ctx
        self.roles = []
        [self.add_item(RolesButton(f'{i}', self)) for i in list_roles[0:-1]]

    async def on_timeout(self):  # таймер выбора роли
        self.roles = [item.label for item in self.children if item.disabled]
        global roles
        await self.ctx.purge(limit=1)
        if len(self.roles) > 1:  # если участвуют больше 1
            roles = self.roles
            view = View()
            [view.add_item(TableButton(f'{i}', self.roles)) for i in os.listdir('elementary')]
            await self.ctx.send(view=view)
        else:  # иначе завершить выполнение
            await bot.close()


class RolesButton(Button):  # выбор роли
    def __init__(self, label, ctx):
        super().__init__(label=label)
        self.ctx = ctx

    async def callback(self, interaction):  # нажатие кнопки роли
        if len(interaction.user.roles) > 1:  # каждый может взять не больше 1 роли
            return
        get_role = discord.utils.get(interaction.guild.roles, name=self.label)
        await interaction.user.add_roles(get_role)
        self.disabled = True  # когда роль выбрана, кнопка становится не активной
        await interaction.response.edit_message(view=self.ctx)


class TableButton(Button):  # выбор игры
    def __init__(self, label, roles):
        super().__init__(label=label)
        self.roles = roles
        self.numb = [x for x in range(2, 33)]
        self.path = None

    async def callback(self, interaction):  # нажатие кнопки выбора игры
        global turn_now, turns
        turns = (x for x in self.roles)
        turn_now = next(turns)
        self.path = os.path.join(os.getcwd(), f'elementary/{self.label}')
        start = discord.File(f'{self.path}/34.png', filename=f'34.png')
        embed = discord.Embed(title=f'{self.label}', colour=discord.Colour.from_rgb(248, 254, 1))
        embed.set_image(url=f"attachment://{start.filename}")
        preview = [discord.File(f'{self.path}/{page}.png', filename=f'{page}.png') for page in [33, 1]]
        await interaction.message.delete()
        await interaction.channel.send(embed=embed, file=start)
        await interaction.channel.send(files=preview)

        self.path = os.path.join(self.path, 'карты')
        for role in self.roles:  # каждой из роли отправить первые 3 карты
            channel = discord.utils.get(bot.get_all_channels(), name=f'{role}')
            pages = self.sample(3)
            cards = [discord.File(f'{self.path}/{page}.png', filename=f'{page}.png') for page in pages]
            await channel.send(files=cards)
            view = PersonalView(pages, channel, cards, self.path, role, self.numb)
            await channel.send(view=view)

    def sample(self, qty):  # рандомные числа из списка оставшихся карт
        rand = random(self.numb, qty)
        [self.numb.remove(x) for x in rand]
        return rand


class PersonalView(View):  # персональное представление
    def __init__(self, pages, channel, cards, path, role, numb):
        super().__init__()
        self.pages = pages
        self.channel = channel
        self.cards = cards
        self.path = path
        self.role = role
        self.numb = numb
        self.answer = {}
        [self.add_item(PersonalButtonPage(f'{page}', self, self.role)) for page in pages]

    async def on_error(self, error, item, interaction):  # повторный вызов представления, завершение выбора
        await self.channel.purge(limit=2)
        channel = discord.utils.get(bot.get_all_channels(), name=f'{self.answer["action"]}')
        await channel.send(
            file=discord.File(f'{self.path}/'f'{self.answer["number"]}.png', filename=f'{self.answer["number"]}.png'))
        self.cards.pop(self.pages.index(int(self.answer['number'])))
        self.pages.remove(int(self.answer['number']))
        self.cards = [discord.File(f'{self.path}/{self.cards[0].filename}'),
                      discord.File(f'{self.path}/{self.cards[1].filename}')]

        if len(self.numb) > 0:  # проверка, остались ли карты в колоде
            await self.send_personal_cards()
        else:  # иначе не добавлять больше карт
            await self.channel.purge(limit=1)
            await self.channel.send(files=self.cards)
            view = LastView(self.pages, self.channel, self.cards, self.path, self.role)
            await self.channel.send(view=view)

    async def send_personal_cards(self):  # отправка по одной карте после хода всем ролям
        self.pages.append(self.sample(1)[0])
        self.cards = [discord.File(f'{self.path}/{self.cards[0].filename}', filename=f'{self.cards[0].filename}'),
                      discord.File(f'{self.path}/{self.cards[1].filename}', filename=f'{self.cards[1].filename}'),
                      discord.File(f'{self.path}/{self.pages[-1]}.png', filename=f'{self.pages[-1]}.png')]
        await self.channel.send(files=self.cards)
        view = PersonalView(self.pages, self.channel, self.cards, self.path, self.role, self.numb)
        await self.channel.send(view=view)

    def sample(self, qty):  # рандомные числа из списка оставшихся карт
        rand = random(self.numb, qty)
        [self.numb.remove(x) for x in rand]
        return rand


class PersonalButtonPage(Button):  # выбор карты
    def __init__(self, label, ctx, role):
        super().__init__(label=label)
        self.ctx = ctx
        self.role = role

    async def callback(self, interaction):  # нажатие кнопки номера карты
        self.ctx.answer['number'] = self.label
        self.ctx.clear_items()
        [self.ctx.add_item(PersonalButtonAction(act, self.ctx, self.role)) for act in ['table', 'pass']]
        await interaction.response.edit_message(view=self.ctx)


class PersonalButtonAction(Button):  # выбор действия
    def __init__(self, label, ctx, role):
        super().__init__(label=label)
        self.ctx = ctx
        self.role = role

    async def callback(self, interaction):  # нажатие кнопки действия(в сброс или на стол)
        global turn_now, turns, roles
        if turn_now == self.role:
            turn_now = next(turns)
            if turn_now == roles[-1]:
                turns = (x for x in roles)
            self.ctx.answer['action'] = self.label
            await self.ctx()


class LastView(View):  # отправка последних карт на стол или в пасс без выдачи новых
    def __init__(self, pages, channel, cards, path, role):
        super().__init__()
        self.pages = pages
        self.channel = channel
        self.cards = cards
        self.path = path
        self.role = role
        self.answer = {}
        [self.add_item(PersonalButtonPage(f'{page}', self, self.role)) for page in pages]

    async def on_error(self, error, item, interaction):  # повторный вызов представления, завершение выбора
        await self.channel.purge(limit=2)
        channel = discord.utils.get(bot.get_all_channels(), name=f'{self.answer["action"]}')
        await channel.send(
            file=discord.File(f'{self.path}/'f'{self.answer["number"]}.png', filename=f'{self.answer["number"]}.png'))
        self.cards.pop(self.pages.index(int(self.answer['number'])))
        self.pages.remove(int(self.answer['number']))
        self.cards = [discord.File(f'{self.path}/{self.cards[i].filename}') for i in range(len(self.cards))]
        if len(self.cards) > 0:  # проверка, остались ли карты на руке
            await self.send_personal_cards()
        else:  # иначе отправить кнопка готов
            await self.channel.purge(limit=1)
            view = View()
            view.add_item(ReadyButton('Готов', view, self.channel, self.path))
            await self.channel.send(view=view)

    async def send_personal_cards(self):  # повторный вызов LastView, без выдачи новых карт
        await self.channel.send(files=self.cards)
        view = LastView(self.pages, self.channel, self.cards, self.path, self.role)
        await self.channel.send(view=view)


class ReadyButton(Button):  # кнопка готов
    def __init__(self, label, ctx, channel, path):
        super().__init__(label=label)
        self.ctx = ctx
        self.channel = channel
        self.path = path

    async def callback(self, interaction):  # нажатие кнопки роли
        global ready, roles
        ready += 1
        await self.channel.purge(limit=1)
        remove_role = discord.utils.get(interaction.guild.roles, name=f'{self.channel.name}')
        await interaction.user.remove_roles(remove_role)
        if ready == len(roles):  # если все роли нажали готов, отправлять вопросы и ответы
            channel = discord.utils.get(bot.get_all_channels(), name='table')
            os.chdir(self.path)
            os.chdir("..")
            self.path = os.path.join(os.getcwd(), 'вопросы')
            file = [discord.File(f'{self.path}/{page}.png', filename=f'{page}.png') for page in range(43, 35, -1)]
            await channel.send(files=file)
            users = bot.get_all_members()
            get_role = discord.utils.get(channel.guild.roles, name='pass')
            [await user.add_roles(get_role) for user in users if user.bot is False]
            await bot.close()


bot.run('TOKEN')
