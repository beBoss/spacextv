<div align="center">

<img src="plugin.program.spacextv/resources/icon.png" width="150" alt="SpaceXTV">

# SpaceXTV

**Bulsat live TV and TV guide for Kodi - fast even on low-power Android TV boxes.**<br>
**Bulsat телевизия на живо и ТВ програма за Kodi - бърза дори на слаби Android TV боксове.**

[![Version](https://img.shields.io/github/v/release/beBoss/spacextv?label=version&color=f26b3a)](https://github.com/beBoss/spacextv/releases/latest)
[![Kodi 19 | 20 | 21](https://img.shields.io/badge/Kodi-19%20%7C%2020%20%7C%2021-17B2E7?logo=kodi&logoColor=white)](https://kodi.tv)
[![License GPL-3.0](https://img.shields.io/badge/license-GPL--3.0-blue)](LICENSE.txt)

**English** · [Български](#български)

<img src="screenshots/08-channels.jpg" width="760" alt="SpaceXTV channels with TV guide in Kodi">

</div>

## English

> [!IMPORTANT]
> You need **Kodi 19 or newer** (Android, Windows, Mac, Linux, LibreELEC) and an active **Bulsat** subscription.

### Install - 7 steps, about 2 minutes

The address you add in Kodi:

```
https://beboss.github.io/spacextv/
```

```text
1  Settings → System → Add-ons → Unknown sources → ON → Yes
2  Settings → File manager → Add source → <None> → type the address above → name it SpaceXTV → OK
3  Add-ons → Install from zip file → SpaceXTV → repository.spacextv.zip
4  Add-ons → Install from repository → SpaceXTV Repository → Program add-ons → SpaceXTV → Install
5  "Welcome to SpaceXTV" → Sign in → your Bulsat username and password
6  "Add-on required: IPTV Simple Client" → Yes
7  Wait until the messages in the top-right corner are gone → open TV
```

> [!TIP]
> That's all. SpaceXTV keeps your channels and TV guide fresh by itself, and Kodi keeps SpaceXTV up to date.

### Step by step, with screenshots

<details>
<summary><b>1 · Allow unknown sources</b></summary>
<br>

**Settings → System → Add-ons** → turn on **Unknown sources** → **Yes**.

<img src="screenshots/01-unknown-sources.jpg" width="49%">
</details>

<details>
<summary><b>2 · Add the SpaceXTV address</b></summary>
<br>

**Settings → File manager → Add source** → **&lt;None&gt;** → type `https://beboss.github.io/spacextv/` → name it **SpaceXTV** → **OK**.

<img src="screenshots/02-file-manager.jpg" width="49%"> <img src="screenshots/02a-add-source.jpg" width="49%">
<img src="screenshots/02b-source-address.jpg" width="49%"> <img src="screenshots/02c-source-added.jpg" width="49%">
</details>

<details>
<summary><b>3 · Install the SpaceXTV Repository</b></summary>
<br>

**Add-ons → Install from zip file → SpaceXTV → repository.spacextv.zip** → wait for *"Add-on installed"*.

<img src="screenshots/03-install-from-zip.jpg" width="49%"> <img src="screenshots/03a-repository-zip.jpg" width="49%">
<img src="screenshots/03b-repository-installed.jpg" width="49%">
</details>

<details>
<summary><b>4 · Install SpaceXTV</b></summary>
<br>

**Add-ons → Install from repository → SpaceXTV Repository → Program add-ons → SpaceXTV → Install**.

<img src="screenshots/04-install-from-repository.jpg" width="49%"> <img src="screenshots/04a-spacextv-repository.jpg" width="49%">
<img src="screenshots/04b-program-add-ons.jpg" width="49%"> <img src="screenshots/04c-spacextv-installed.jpg" width="49%">
</details>

<details>
<summary><b>5 · Sign in</b></summary>
<br>

The **Welcome to SpaceXTV** window appears by itself → **Sign in** → type your Bulsat username and password.

<img src="screenshots/05-welcome-sign-in.jpg" width="49%">
</details>

<details>
<summary><b>6 · Allow PVR IPTV Simple Client</b></summary>
<br>

If Kodi asks for **IPTV Simple Client** → **Yes**. SpaceXTV sets it up for you - nothing to configure.

<img src="screenshots/06-iptv-simple-required.jpg" width="49%"> <img src="screenshots/06a-installing-iptv-simple.jpg" width="49%">
</details>

<details>
<summary><b>7 · Wait for the messages to finish</b></summary>
<br>

Watch the top-right corner. In about a minute you will see, one after another:

| Message | What happens |
|---|---|
| `SpaceXTV: … TV guide 56/196` | SpaceXTV downloads the TV guide |
| `Loading channels into Live TV, please wait…` | SpaceXTV loads the channels into Kodi |
| `PVR manager is starting up` | Kodi starts Live TV |
| `All set! … channels - open TV in the Kodi main menu` | The channels are ready |
| `Importing guide from clients` | Kodi fills in the TV guide - wait until it is gone |

<img src="screenshots/07-loading-tv-guide.jpg" width="49%"> <img src="screenshots/07a-loading-live-tv.jpg" width="49%">
<img src="screenshots/07b-pvr-starting.jpg" width="49%"> <img src="screenshots/07c-all-set.jpg" width="49%">
</details>

<details>
<summary><b>8 · Watch</b></summary>
<br>

Open **TV** in the main menu → **Channels** or **Guide**.

<img src="screenshots/08a-tv-home.jpg" width="49%"> <img src="screenshots/08-channels.jpg" width="49%">
</details>

<details>
<summary><b>Optional · Adult channels (18+)</b></summary>
<br>

**Add-ons** → highlight **SpaceXTV** → hold **OK** (or press the menu key) → **Settings → Channels** → turn on **Show adult channels (18+)** → **OK**.
SpaceXTV reloads by itself and shows *"Done: … channels, TV guide 3 days"*.

<img src="screenshots/09-spacextv-add-on.jpg" width="49%"> <img src="screenshots/09b-settings.jpg" width="49%">
<img src="screenshots/09c-adult-channels.jpg" width="49%"> <img src="screenshots/09d-done.jpg" width="49%">
</details>

<details>
<summary><b>Without the repository</b> (no automatic updates)</summary>
<br>

Download `plugin.program.spacextv-….zip` from [Releases](https://github.com/beBoss/spacextv/releases/latest) → copy it to a USB stick → step 1 → **Add-ons → Install from zip file** → pick the zip → steps 5-8.
</details>

Missed the welcome window? **Add-ons → Program add-ons → SpaceXTV → Sign in and load channels**.

### How it works

| When | What SpaceXTV does |
|---|---|
| First start | Asks for your username and password, sets up PVR IPTV Simple Client, loads the channels and TV guide |
| About every 9 hours | Gets fresh links before the old ones expire |
| Every 12 hours | Refreshes the TV guide (3 days ahead) |
| Something changed | Reloads Live TV - never while you are watching |
| A channel won't start | Checks the link; if Bulsat stopped it - signs in again and starts the channel (about 30 s) |
| Kodi starts | Quick link check (under 1 s) - fixes them before you pick a channel |
| Settings changed (e.g. 18+) | Applies them right away |

### What's better than the older add-ons

- Rewritten from scratch for Kodi 19, 20 and 21.
- One step: just username and password - no folders, hidden files or IPTV Simple settings.
- Fresh links right before the old ones expire (about every 9 hours instead of every hour) - fewer reloads.
- Live TV reloads only when something changed, never while you are watching.
- Fixes stopped channels by itself.
- Light TV guide - fast even on cheap Android boxes.
- Updates itself from the repository.
- English and Bulgarian - follows Kodi's language.
- Built-in log: **SpaceXTV → Show SpaceXTV log**.
- Open source (GPL-3.0) - connects only to Bulsat's servers.

### Problems

| You see | Do this |
|---|---|
| "Could not connect to repository" | Check the box's date and time (see below), then try again |
| Channels play, but no TV guide | The box's date or time is wrong: Android **Settings → Date & time** → **Automatic**, correct time zone |
| "Login failed" | Check username and password: SpaceXTV → Settings → Account |
| "Update failed - no internet?" | Check the connection - SpaceXTV retries by itself |
| A channel won't start ("playback failed") | Nothing - SpaceXTV gets fresh links by itself and starts the channel within about 30 s |
| "Bulsat refuses the channels" | Your account is in use on another device - SpaceXTV tries again by itself in 30 min |
| No "TV" in the main menu | SpaceXTV → **Set up Live TV** |
| Kodi refuses the zip | Do step 1 |
| "Failed to install dependencies" | Needs internet - Kodi downloads the required modules from its official repository |
| Linux (Ubuntu / Debian) | First install: `sudo apt install kodi-pvr-iptvsimple` |

> [!TIP]
> **Slow box?** Settings → PVR & Live TV → Guide → turn on **Prevent updates while playing**.

### Questions and answers

<details><summary><b>Is it free?</b></summary>

Yes. You only need a Bulsat subscription.
</details>

<details><summary><b>Does it send my data anywhere?</b></summary>

No. SpaceXTV connects only to Bulsat's servers. Your username and password stay in Kodi's settings on your device. The code is public - anyone can check it.
</details>

<details><summary><b>How does it update?</b></summary>

By itself, from the repository - Kodi checks when it starts and once a day.
</details>

<details><summary><b>I'm coming from Space Plug-In</b></summary>

Your settings are copied over and the old add-on is switched off. You can uninstall it afterwards.
</details>

<details><summary><b>4K channels?</b></summary>

SpaceXTV → Settings → Account → **Device profile: Android TV** - adds 5 channels in 4K, but no 18+.
</details>

<details><summary><b>I also watch on another device</b></summary>

If the same account signs in on another device, Bulsat may stop the links on the first one. SpaceXTV signs in again by itself when you use Kodi.
</details>

<details><summary><b>Something doesn't work?</b></summary>

SpaceXTV → **Show SpaceXTV log** → take a photo of the screen and send it with your question.
</details>

<br>

---

## Български

[English](#english) · **Български**

> [!IMPORTANT]
> Нужни са **Kodi 19 или по-нов** (Android, Windows, Mac, Linux, LibreELEC) и активен абонамент за **Bulsat**.

### Инсталиране - 7 стъпки, около 2 минути

Адресът, който добавяте в Kodi:

```
https://beboss.github.io/spacextv/
```

```text
1  Настройки → Система → Добавки → Неизвестни източници → включете → Да
2  Настройки → Файлов мениджър → Добавяне на източник → <Няма> → адреса отгоре → име SpaceXTV → OK
3  Добавки → Инсталиране от zip файл → SpaceXTV → repository.spacextv.zip
4  Добавки → Инсталиране от хранилище → SpaceXTV Repository → Програмни добавки → SpaceXTV → Инсталиране
5  „Добре дошли в SpaceXTV“ → Вход → потребителско име и парола за Bulsat
6  Kodi пита за IPTV Simple Client → Да
7  Изчакайте съобщенията горе вдясно да изчезнат → отворете Телевизия
```

> [!TIP]
> Това е всичко. SpaceXTV сам поддържа каналите и ТВ програмата актуални, а Kodi сам обновява SpaceXTV.

### Стъпка по стъпка, със снимки

Снимките са от Kodi на английски - в скоби са имената на английски.

<details>
<summary><b>1 · Разрешете неизвестни източници</b></summary>
<br>

**Настройки → Система → Добавки** *(Settings → System → Add-ons)* → включете **Неизвестни източници** *(Unknown sources)* → **Да**.

<img src="screenshots/01-unknown-sources.jpg" width="49%">
</details>

<details>
<summary><b>2 · Добавете адреса на SpaceXTV</b></summary>
<br>

**Настройки → Файлов мениджър → Добавяне на източник** *(Settings → File manager → Add source)* → **&lt;Няма&gt;** → въведете `https://beboss.github.io/spacextv/` → име **SpaceXTV** → **OK**.

<img src="screenshots/02-file-manager.jpg" width="49%"> <img src="screenshots/02a-add-source.jpg" width="49%">
<img src="screenshots/02b-source-address.jpg" width="49%"> <img src="screenshots/02c-source-added.jpg" width="49%">
</details>

<details>
<summary><b>3 · Инсталирайте хранилището SpaceXTV</b></summary>
<br>

**Добавки → Инсталиране от zip файл** *(Add-ons → Install from zip file)* → **SpaceXTV → repository.spacextv.zip** → изчакайте съобщението, че е инсталирана.

<img src="screenshots/03-install-from-zip.jpg" width="49%"> <img src="screenshots/03a-repository-zip.jpg" width="49%">
<img src="screenshots/03b-repository-installed.jpg" width="49%">
</details>

<details>
<summary><b>4 · Инсталирайте SpaceXTV</b></summary>
<br>

**Добавки → Инсталиране от хранилище** *(Install from repository)* → **SpaceXTV Repository → Програмни добавки** *(Program add-ons)* → **SpaceXTV → Инсталиране**.

<img src="screenshots/04-install-from-repository.jpg" width="49%"> <img src="screenshots/04a-spacextv-repository.jpg" width="49%">
<img src="screenshots/04b-program-add-ons.jpg" width="49%"> <img src="screenshots/04c-spacextv-installed.jpg" width="49%">
</details>

<details>
<summary><b>5 · Вход</b></summary>
<br>

Прозорецът **Добре дошли в SpaceXTV** се появява сам → **Вход** → въведете потребителското име и паролата си за Bulsat.

<img src="screenshots/05-welcome-sign-in.jpg" width="49%">
</details>

<details>
<summary><b>6 · Разрешете PVR IPTV Simple Client</b></summary>
<br>

Ако Kodi попита за **IPTV Simple Client** → **Да**. SpaceXTV го настройва сам - нищо не настройвате.

<img src="screenshots/06-iptv-simple-required.jpg" width="49%"> <img src="screenshots/06a-installing-iptv-simple.jpg" width="49%">
</details>

<details>
<summary><b>7 · Изчакайте съобщенията</b></summary>
<br>

Гледайте горния десен ъгъл. За около минута ще видите едно след друго:

| Съобщение | Какво става |
|---|---|
| `SpaceXTV: … ТВ програма 56/196` | SpaceXTV изтегля ТВ програмата |
| `Зареждане на каналите в телевизията, моля изчакайте…` | SpaceXTV зарежда каналите в Kodi |
| `PVR manager is starting up` | Kodi пуска телевизията |
| `Готово! … канала - отворете Телевизия от главното меню` | Каналите са готови |
| `Importing guide from clients` | Kodi попълва ТВ програмата - изчакайте да изчезне |

<img src="screenshots/07-loading-tv-guide.jpg" width="49%"> <img src="screenshots/07a-loading-live-tv.jpg" width="49%">
<img src="screenshots/07b-pvr-starting.jpg" width="49%"> <img src="screenshots/07c-all-set.jpg" width="49%">
</details>

<details>
<summary><b>8 · Гледайте</b></summary>
<br>

Отворете **Телевизия** *(TV)* от главното меню → **Канали** или **Програма**.

<img src="screenshots/08a-tv-home.jpg" width="49%"> <img src="screenshots/08-channels.jpg" width="49%">
</details>

<details>
<summary><b>По желание · Канали за възрастни (18+)</b></summary>
<br>

**Добавки** → застанете на **SpaceXTV** → задръжте **OK** (или бутона за меню) → **Настройки → Канали** → включете **Показване на канали за възрастни (18+)** → **OK**.
SpaceXTV презарежда сам и показва *„Готово: … канала, ТВ програма за 3 дн.“*.

<img src="screenshots/09-spacextv-add-on.jpg" width="49%"> <img src="screenshots/09b-settings.jpg" width="49%">
<img src="screenshots/09c-adult-channels.jpg" width="49%"> <img src="screenshots/09d-done.jpg" width="49%">
</details>

<details>
<summary><b>Без хранилище</b> (без автоматично обновяване)</summary>
<br>

Свалете `plugin.program.spacextv-….zip` от [Releases](https://github.com/beBoss/spacextv/releases/latest) → копирайте го на USB → стъпка 1 → **Добавки → Инсталиране от zip файл** → изберете zip файла → стъпки 5-8.
</details>

Пропуснахте прозореца за вход? **Добавки → Програмни добавки → SpaceXTV → Вход и зареждане на каналите**.

### Как работи

| Кога | Какво прави SpaceXTV |
|---|---|
| Първо пускане | Пита за име и парола, настройва PVR IPTV Simple Client, зарежда каналите и ТВ програмата |
| Приблизително на всеки 9 часа | Взима нови линкове, преди старите да изтекат |
| На всеки 12 часа | Обновява ТВ програмата (3 дни напред) |
| Нещо се е променило | Презарежда телевизията - никога докато гледате |
| Канал не тръгва | Проверява линка; ако Bulsat го е спрял - влиза наново и пуска канала (приблизително 30 сек.) |
| При пускане на Kodi | Бърза проверка на линковете (под 1 сек.) - оправя ги, преди да изберете канал |
| Променени настройки (напр. 18+) | Прилага ги веднага |

### Какво е по-добре от старите адони

- Написан наново от нулата за Kodi 19, 20 и 21.
- Една стъпка: само име и парола - без папки, скрити файлове и настройки на IPTV Simple.
- Нови линкове точно преди старите да изтекат (приблизително на 9 часа вместо на всеки час) - по-малко презареждания.
- Телевизията се презарежда само при промяна и никога докато гледате.
- Сам оправя спрели канали.
- Лека ТВ програма - бърз и на евтини Android боксове.
- Обновява се сам през хранилището.
- Български и английски - според езика на Kodi.
- Вграден дневник: **SpaceXTV → Покажи дневника на SpaceXTV**.
- Отворен код (GPL-3.0) - свързва се само със сървърите на Bulsat.

### Проблеми

| Виждате | Направете |
|---|---|
| „Could not connect to repository“ | Проверете датата и часа на бокса (вижте долу) и опитайте пак |
| Каналите вървят, но няма ТВ програма | Датата или часът на бокса са грешни: Android **Настройки → Дата и час** → **Автоматично**, часова зона **София** |
| „Неуспешен вход“ | Проверете името и паролата: SpaceXTV → Настройки → Акаунт |
| „Неуспешно обновяване - няма интернет?“ | Проверете интернета - SpaceXTV опитва пак сам |
| Канал не тръгва („неуспешно възпроизвеждане“) | Нищо - SpaceXTV сам взима нови връзки и пуска канала след приблизително 30 сек. |
| „Bulsat отказва каналите“ | Акаунтът се ползва на друго устройство - SpaceXTV опитва пак сам след 30 мин. |
| Няма „Телевизия“ в главното меню | SpaceXTV → **Настрой телевизията** |
| Kodi не приема zip файла | Направете стъпка 1 |
| „Неуспешно инсталиране на зависимости“ | Нужен е интернет - Kodi сваля нужните модули от официалното си хранилище |
| Linux (Ubuntu / Debian) | Първо инсталирайте: `sudo apt install kodi-pvr-iptvsimple` |

> [!TIP]
> **Слаб бокс?** Настройки → PVR и ТВ на живо → Програма → включете **Prevent updates while playing**.

### Въпроси и отговори

<details><summary><b>Безплатен ли е?</b></summary>

Да. Нужен е само абонамент за Bulsat.
</details>

<details><summary><b>Изпраща ли данните ми някъде?</b></summary>

Не. SpaceXTV се свързва само със сървърите на Bulsat. Името и паролата остават в настройките на Kodi на вашето устройство. Кодът е публичен - всеки може да провери.
</details>

<details><summary><b>Как се обновява?</b></summary>

Сам, през хранилището - Kodi проверява при пускане и веднъж на ден.
</details>

<details><summary><b>Идвам от Space Plug-In</b></summary>

Настройките се прехвърлят сами, а старият адон се изключва. После може да го деинсталирате.
</details>

<details><summary><b>Канали в 4K?</b></summary>

SpaceXTV → Настройки → Акаунт → **Профил на устройството: Android TV** - добавя 5 канала в 4K, но без 18+.
</details>

<details><summary><b>Гледам и на друго устройство</b></summary>

Ако същият акаунт влезе на друго устройство, Bulsat може да спре линковете на първото. SpaceXTV влиза наново сам, когато ползвате Kodi.
</details>

<details><summary><b>Нещо не работи?</b></summary>

SpaceXTV → **Покажи дневника на SpaceXTV** → снимайте екрана и го пратете заедно с въпроса си.
</details>

<br>

---

<div align="center">

**SpaceXTV** by **Blagovest Klisarski** · <https://blagovestklisarski.com>

License [GPL-3.0](LICENSE.txt) · Thanks to **harrygg** and **kodi1** for the original bscfusion add-on.

Requires an active Bulsat subscription. Not affiliated with Bulsatcom.<br>
Изисква активен абонамент за Bulsat. Не е свързан с Булсатком.

</div>
