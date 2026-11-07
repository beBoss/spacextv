# SpaceXTV

Bulsat телевизия на живо и ТВ програма за Kodi - бърза дори на слаби Android TV боксове.
Bulsat live TV and TV guide for Kodi - fast even on low-power Android TV boxes.

Автор / Author: **Blagovest Klisarski** - <https://blagovestklisarski.com>

**[Български](#български)** · **[English](#english)** · Сваляне / Download: [repository.spacextv.zip](https://beboss.github.io/spacextv/repository.spacextv.zip)

<!-- screenshots: put them in screenshots/ and add them here -->

---

## Български

### Инсталиране (около 2 минути)

Нужни са само: **Kodi 19 или по-нов** и **абонамент за Bulsat**.

1. **Настройки → Система → Добавки → Неизвестни източници** *(Settings → System → Add-ons → Unknown sources)* → включете → **Да**.
2. **Настройки → Файлов мениджър → Добавяне на източник** *(Settings → File manager → Add source)* → **&lt;Няма&gt;** → въведете `https://beboss.github.io/spacextv/` → **OK** → **OK**.
3. **Добавки → Инсталиране от zip файл** *(Add-ons → Install from zip file)* → **spacextv** → `repository.spacextv.zip`.
4. **Добавки → Инсталиране от хранилище** *(Install from repository)* → **SpaceXTV Repository** → **Програмни добавки** → **SpaceXTV** → **Инсталиране**.
5. Появява се прозорец **Добре дошли в SpaceXTV** → натиснете **Вход** → въведете потребителското име и паролата си за Bulsat.
6. Ако Kodi попита за **PVR IPTV Simple Client** → **Да**.
7. Изчакайте около минута, докато се появи **„Готово! … отворете Телевизия от главното меню“** → отворете **Телевизия**. Готово!

Оттук нататък Kodi обновява SpaceXTV сам.

**Без хранилище:** свалете `plugin.program.spacextv-….zip` от [Releases](https://github.com/beBoss/spacextv/releases/latest) → копирайте го на USB → стъпка 1 → **Инсталиране от zip файл** → стъпки 5-7. Така няма автоматично обновяване.

SpaceXTV говори български, когато Kodi е на български.

**Всичко останало е автоматично** - пътищата до файловете, PVR IPTV Simple Client, ТВ програмата и обновяването.
Не е нужно да търсите папки, да показвате скрити файлове или да настройвате IPTV Simple ръчно - на всяко устройство (Android, Windows, Mac, Linux, LibreELEC).

Пропуснахте прозореца? Отворете **SpaceXTV** от **Добавки** → **Вход и зареждане на каналите**.

### Всеки ден

Нищо не правите. SpaceXTV работи сам във фонов режим: обновява каналите преди линковете да изтекат (приблизително на всеки 9 часа), обновява ТВ програмата и презарежда телевизията само при промяна - никога докато гледате.

### Как работи

| Кога | Какво прави SpaceXTV |
|---|---|
| Първо пускане | Пита за име и парола, настройва PVR IPTV Simple Client, зарежда каналите и ТВ програмата |
| Приблизително на всеки 9 часа | Взима нови линкове, преди старите да изтекат |
| На всеки 12 часа | Обновява ТВ програмата (3 дни напред) |
| Нещо се е променило | Презарежда телевизията - никога докато гледате |
| Канал не тръгва | Проверява линка; ако Bulsat го е спрял - влиза наново и пуска канала (приблизително 30 сек.) |
| При пускане на Kodi | Бърза проверка на линковете (под 1 сек.) - оправя ги, преди да натиснете канал |
| Променени настройки (напр. 18+) | Прилага ги веднага |

### Какво е по-добре от старите адони

- Написан наново от нулата за Kodi 19, 20 и 21.
- Една стъпка: само име и парола - без папки, скрити файлове и настройки на IPTV Simple.
- Нови линкове точно преди старите да изтекат (на приблизително 9 часа вместо на всеки час) - по-малко презареждания.
- Телевизията се презарежда само при промяна и никога докато гледате.
- Сам оправя спрели канали.
- Лека ТВ програма - бърз и на евтини Android боксове.
- Обновява се сам през хранилището.
- Български и английски.
- Вграден дневник: **SpaceXTV → Покажи дневника на SpaceXTV**.
- Отворен код (GPL-3.0) - свързва се само със сървърите на Bulsat.

### Проблеми

| Виждате | Направете |
|---|---|
| „Неуспешен вход“ | Проверете името и паролата: SpaceXTV → Настройки → Акаунт |
| „Неуспешно обновяване - няма интернет?“ | Проверете интернета - SpaceXTV опитва пак сам |
| Канал не тръгва („неуспешно възпроизвеждане“) | Нищо - SpaceXTV сам взима нови връзки и пуска канала след приблизително 30 сек. |
| „Bulsat отказва каналите“ | Акаунтът се ползва на друго устройство - SpaceXTV опитва пак сам след 30 мин. |
| Каналите вървят, но няма ТВ програма | Датата или часът на бокса са грешни: Android **Настройки → Дата и час** → **Автоматично**, часова зона **София** |
| Няма „Телевизия“ в главното меню | SpaceXTV → **Настрой телевизията** |
| Kodi не приема zip файла | Направете стъпка 1 |
| „Неуспешно инсталиране на зависимости“ | Нужен е интернет - Kodi сваля нужните модули от официалното си хранилище |
| Linux (Ubuntu / Debian) | Първо инсталирайте: `sudo apt install kodi-pvr-iptvsimple` |

**Съвет за слаби боксове:** Настройки → PVR и ТВ на живо → Програма → включете **Prevent updates while playing**.

### Въпроси и отговори

**Безплатен ли е?** Да. Нужен е само абонамент за Bulsat.

**Изпраща ли данните ми някъде?** Не. SpaceXTV се свързва само със сървърите на Bulsat. Името и паролата остават в настройките на Kodi на вашето устройство. Кодът е публичен - всеки може да провери.

**Как се обновява?** Сам, през хранилището - Kodi проверява при пускане и веднъж на ден.

**Идвам от Space Plug-In.** Настройките се прехвърлят сами, а старият адон се изключва. После може да го деинсталирате.

**Канали 18+?** SpaceXTV → Настройки → Канали → **Показване на канали за възрастни (18+)**.

**Канали в 4K?** SpaceXTV → Настройки → Акаунт → **Профил на устройството: Android TV** - добавя 5 канала в 4K, но без 18+.

**Гледам и на друго устройство.** Ако същият акаунт влезе на друго устройство, Bulsat може да спре линковете на първото. SpaceXTV влиза наново сам, когато ползвате Kodi.

**Нещо не работи?** SpaceXTV → **Покажи дневника на SpaceXTV** → снимайте екрана и го пратете заедно с въпроса си.

---

## English

### Install (about 2 minutes)

You only need **Kodi 19 or newer** and a **Bulsat subscription**.

1. **Settings → System → Add-ons → Unknown sources** → turn on → **Yes**.
2. **Settings → File manager → Add source** → **&lt;None&gt;** → type `https://beboss.github.io/spacextv/` → **OK** → **OK**.
3. **Add-ons → Install from zip file** → **spacextv** → `repository.spacextv.zip`.
4. **Add-ons → Install from repository** → **SpaceXTV Repository** → **Program add-ons** → **SpaceXTV** → **Install**.
5. A **Welcome to SpaceXTV** window appears → **Sign in** → type your Bulsat username and password.
6. If Kodi asks about **PVR IPTV Simple Client** → **Yes**.
7. Wait about a minute for **"All set! … open TV in the Kodi main menu"** → open **TV**. Done!

From now on Kodi keeps SpaceXTV up to date by itself.

**Without the repository:** download `plugin.program.spacextv-….zip` from [Releases](https://github.com/beBoss/spacextv/releases/latest) → copy it to a USB stick → step 1 → **Install from zip file** → steps 5-7. No automatic updates this way.

SpaceXTV follows Kodi's language (English / Bulgarian).

**Everything else is automatic** - file paths, PVR IPTV Simple Client, TV guide and updates.
No folders to find, no hidden files to show, no manual IPTV Simple setup - on any device (Android, Windows, Mac, Linux, LibreELEC).

Missed the window? **Add-ons → Program add-ons → SpaceXTV → Sign in and load channels**.

### Every day

Nothing to do. SpaceXTV works in the background: refreshes the channels before the stream links expire (about every 9 hours), refreshes the TV guide, and reloads Live TV only when something changed - never while you are watching.

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
- Bulgarian and English.
- Built-in log: **SpaceXTV → Show SpaceXTV log**.
- Open source (GPL-3.0) - connects only to Bulsat's servers.

### Problems

| You see | Do this |
|---|---|
| "Login failed" | Check username and password: SpaceXTV → Settings → Account |
| "Update failed - no internet?" | Check the connection - SpaceXTV retries by itself |
| A channel won't start ("playback failed") | Nothing - SpaceXTV gets fresh links by itself and starts the channel within about 30 s |
| "Bulsat refuses the channels" | Your account is in use on another device - SpaceXTV tries again by itself in 30 min |
| Channels play, but no TV guide | The box's date or time is wrong: Android **Settings → Date & time** → **Automatic**, time zone **Sofia** |
| No "TV" in the main menu | SpaceXTV → **Set up Live TV** |
| Kodi refuses the zip | Do step 1 |
| "Failed to install dependencies" | Needs internet - Kodi downloads the required modules from its official repository |
| Linux (Ubuntu / Debian) | First install: `sudo apt install kodi-pvr-iptvsimple` |

**Tip for slow boxes:** Settings → PVR & Live TV → Guide → turn on **Prevent updates while playing**.

### Questions and answers

**Is it free?** Yes. You only need a Bulsat subscription.

**Does it send my data anywhere?** No. SpaceXTV connects only to Bulsat's servers. Your username and password stay in Kodi's settings on your device. The code is public - anyone can check it.

**How does it update?** By itself, from the repository - Kodi checks at start and once a day.

**I'm coming from Space Plug-In.** Your settings are copied over and the old add-on is switched off. You can uninstall it afterwards.

**18+ channels?** SpaceXTV → Settings → Channels → **Show adult channels (18+)**.

**4K channels?** SpaceXTV → Settings → Account → **Device profile: Android TV** - adds 5 channels in 4K, but no 18+.

**I also watch on another device.** If the same account signs in on another device, Bulsat may stop the links on the first one. SpaceXTV signs in again by itself when you use Kodi.

**Something doesn't work?** SpaceXTV → **Show SpaceXTV log** → take a photo of the screen and send it with your question.

---

Лиценз / License: [GPL-3.0](LICENSE.txt). Благодарности на / Thanks to **harrygg** and **kodi1** for the original bscfusion add-on.

Requires an active Bulsat subscription. Not affiliated with Bulsatcom.
Изисква активен абонамент за Bulsat. Не е свързан с Булсатком.
