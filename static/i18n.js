(() => {
    const info = window.__I18N__ || {lang: 'ru', next: '/'};
    const lang = info.lang === 'en' ? 'en' : 'ru';

    function addLanguageSwitch() {
        const right = document.querySelector('.header-right');
        if (!right || right.querySelector('.lang-switch')) return;
        const next = encodeURIComponent(info.next || '/');
        const box = document.createElement('div');
        box.className = 'lang-switch';
        box.setAttribute('aria-label', 'Language');
        box.innerHTML =
            '<a href="/language/ru?next=' + next + '" class="' + (lang === 'ru' ? 'active' : '') + '" title="Русский">' +
            '<span class="lang-flag flag-ru"></span><span>RU</span></a>' +
            '<a href="/language/en?next=' + next + '" class="' + (lang === 'en' ? 'active' : '') + '" title="English">' +
            '<span class="lang-flag flag-en"></span><span>EN</span></a>';
        const moon = right.querySelector('.moon, .theme-toggle');
        if (moon) right.insertBefore(box, moon);
        else right.appendChild(box);
    }

    addLanguageSwitch();
    if (lang !== 'en') return;

    document.documentElement.lang = 'en';

    const EN = {
        "Вход": "Log in",
        "Войти": "Log in",
        "Выйти": "Log out",
        "Регистрация": "Sign up",
        "Зарегистрироваться": "Create account",
        "Кабинет": "Cabinet",
        "👤 Кабинет": "👤 Cabinet",
        "Привет,": "Hello,",
        "Рейтинг": "Rating",
        "Рейтинг Дуэли": "Duel Rating",
        "Рейтинг дуэли": "Duel Rating",
        "Рейтинг Аркадии": "Arcadia Rating",
        "Ивенты": "Events",
        "Ивентов": "Events",
        "Штат": "State",
        "Карта штата": "State map",
        "Калькулятор": "Calculator",
        "Калькулятор навыков": "Skill calculator",
        "Калькулятор прокачки": "Upgrade calculator",
        "Калькулятор титана (звёзды)": "Titan calculator (stars)",
        "Калькулятор Турбочерепашки": "Turbo Turtle calculator",
        "Общий рейтинг": "Overall rating",
        "Рейтинг Ивентов →": "Events rating →",
        "Главная": "Home",
        "Навигация": "Navigation",
        "Разделы": "Sections",
        "Личный кабинет": "Personal cabinet",
        "Мой профиль": "My profile",
        "Администрирование": "Administration",
        "Панель администратора": "Admin panel",
        "Админ": "Admin",
        "Админ штата": "State admin",
        "Супер-админ": "Super admin",
        "Резервуар": "Reservoir",
        "Игрок": "Player",
        "Роль": "Role",
        "Логин": "Login",
        "Пароль": "Password",
        "Повторите пароль": "Repeat password",
        "Вход | [HEL] Ацкое Пламя": "Log in | [HEL] Ацкое Пламя",
        "Личный кабинет участника союза": "Alliance member cabinet",
        "Создайте личный кабинет и привяжите себя к рейтингу": "Create an account and link yourself to the rating",
        "← На главную": "← Back to home",
        "Добро пожаловать!": "Welcome!",
        "Карусель пока пуста": "The carousel is empty",
        "Добавить первый слайд": "Add the first slide",
        "Изображение не загружено": "Image not loaded",
        "Мои карты": "My maps",
        "Доступ к карте": "Map access",
        "Инструкция": "Instructions",
        "Нарисовать карту": "Draw a map",
        "Управление картами": "Map management",
        "Сохранить": "Save",
        "Сохранить карту": "Save map",
        "Отмена": "Cancel",
        "Закрыть": "Close",
        "Понятно": "Got it",
        "Удалить": "Delete",
        "Очистить": "Clear",
        "Сбросить": "Reset",
        "Рассчитать": "Calculate",
        "Загрузить": "Upload",
        "Выбрать Excel": "Choose Excel",
        "Файл не выбран": "No file selected",
        "Подтвердить": "Confirm",
        "Выберите себя": "Choose yourself",
        "Сохранить легенду": "Save legend",
        "Рисовать": "Draw",
        "Печать": "Print",
        "Подпись блока": "Block label",
        "Текст подписи": "Label text",
        "Введите штат:": "Enter state:",
        "Введите союз:": "Enter union:",
        "Название версии карты:": "Map version name:",
        "Выберите цвета для союзов": "Choose colors for unions",
        "Выберите цвет союза": "Choose a union color",
        "Добавить новый цвет": "Add a new color",
        "Очистить карту?": "Clear the map?",
        "Сезон s3 · новая пустая карта": "Season s3 · new blank map",
        "Инструкция по карте штата": "State map instructions",
        "Как нарисовать карту": "How to draw a map",
        "Сохранение и доступ": "Saving and access",
        "Выберите цвет в палитре и нажмите «Рисовать».": "Pick a color in the palette and press “Draw”.",
        "Инструмент «Ластик» возвращает блоку белый цвет.": "The “Eraser” tool turns a block white.",
        "Инструмент «Буква А» открывает окно подписи блока: введите текст и сохраните.": "The “A” tool opens the block label window: enter text and save it.",
        "Нажмите «Сохранить легенду», чтобы закрепить цвета и названия союзов.": "Press “Save legend” to keep the colors and union names.",
        "Откройте вкладку «Нарисовать карту» и выберите сезон: s1, s2, s3 или s4.": "Open the “Draw a map” tab and choose a season: s1, s2, s3 or s4.",
        "Если нужного цвета нет, нажмите «Добавить новый цвет» и выберите вариант из дополнительной палитры.": "If the color you need is missing, press “Add a new color” and choose from the extra palette.",
        "«Дискета» сохраняет карту: укажите штат, союз и название версии. Карта появится в разделе «Мои карты».": "“Diskette” saves the map: enter the state, union and version name. The map will appear in “My maps”.",
        "«Корзина» очищает карту и легенду. Будьте внимательны: действие затрагивает текущую версию.": "“Trash” clears the map and legend. Be careful: it affects the current version.",
        "«Принтер» сохраняет PNG-изображение карты с палитрой, союзами и подписью автора.": "“Printer” saves a PNG of the map with the palette, unions and author credit.",
        "PNG-файл сохраняется на устройство. На нём будет карта, палитра союзов и подпись: «Карта создана на сайте e-hell.ru, автор карты: ваш логин».": "The PNG is saved to your device. It contains the map, union palette and the credit: “Map created on e-hell.ru, map author: your login”.",
        "Выберите инструмент «Карандаш», выберите цвет в легенде и нажмите «Рисовать». Кликайте по блокам карты, чтобы закрасить их.": "Choose the “Pencil” tool, pick a color in the legend and press “Draw”. Click map blocks to fill them.",
        "Раскройте блок «Выберите цвета для союзов». У каждого цвета есть поле «Союз:» — впишите туда название союза.": "Open “Choose colors for unions”. Each color has a “Union:” field — enter the union name there.",
        "Карта штата — это схема союзов по блокам. Рисовать может любой зарегистрированный пользователь, привязывать ник к рейтингу не обязательно.": "The state map is a block scheme of unions. Any registered user can draw; linking a nickname to the rating is optional.",
        "Внизу карты есть кнопки «Мои карты» и «Доступ к карте». В «Моих картах» хранятся ваши версии и карты, к которым вам дали доступ. Через «Доступ к карте» автор может отметить пользователей, которым разрешено смотреть и редактировать версию.": "At the bottom of the map are “My maps” and “Map access”. “My maps” contains your versions and maps shared with you. Through “Map access” the author can select users allowed to view and edit the version.",
        "Если вы нажмёте «Сохранить», палитра цветов и все внесённые изменения будут удалены. Продолжить?": "If you press “Save”, the color palette and all changes will be deleted. Continue?",
        "Отметьте пользователей, которым разрешено смотреть и редактировать эту версию.": "Select the users allowed to view and edit this version.",
        "О рейтинге": "About the rating",
        "ℹ О рейтинге": "ℹ About the rating",
        "Динамика": "Dynamics",
        "График": "Chart",
        "Пусто": "Empty",
        "Нет данных. Загрузите рейтинг!": "No data. Upload the rating!",
        "Загрузка рейтинга": "Rating upload",
        "Объединение строк": "Merge rows",
        "Объединить": "Merge",
        "Вручить": "Award",
        "Править вручную": "Edit manually",
        "В общий рейтинг": "To overall rating",
        "Управлять болтиками": "Manage bolts",
        "Очки выбранных строк перейдут в:": "Points of selected rows will go to:",
        "Выбрано строк:": "Rows selected:",
        "Связь никнеймов не создаётся — это только перенос очков.": "Nicknames are not linked — only points are transferred.",
        "Дата обновления:": "Updated:",
        "Золотые болтики": "Golden bolts",
        "Посещаемость союзных ивентов. Один золотой болтик — один ивент.": "Alliance event attendance. One golden bolt is one event.",
        "Пока нет золотых болтиков. Админ может вручить их на странице «Золотые болтики».": "No golden bolts yet. An admin can award them on the “Golden bolts” page.",
        "Максимум болтов": "Maximum bolts",
        "Прирост Рост за всё время": "Growth over all time",
        "Дней с болтами Всего замеров": "Days with bolts Total measurements",
        "Болтов сейчас Текущий результат": "Bolts now Current result",
        "Сумма Дуэли, Аркадии и золотых болтиков по неделям": "Duel, Arcadia and golden bolts totals by week",
        "Прогресс:": "Progress:",
        "Прогресс в разделе": "Section progress",
        "← Вернуться к рейтингу": "← Back to rating",
        "Накопленные золотые болтики за ивенты союза": "Accumulated golden bolts for alliance events",
        "Информация об аккаунте": "Account information",
        "Дата регистрации": "Registration date",
        "Отображаемый ник": "Displayed nickname",
        "Всего очков": "Total points",
        "Место в общем": "Overall place",
        "за сезон": "this season",
        "Дарителей:": "Givers:",
        "Кто дарил вам яблоки": "Who gave you apples",
        "Подарили вам за сезон:": "Gifted to you this season:",
        "Осталось подарить на этой неделе:": "Left to gift this week:",
        "Пока никто не дарил вам яблоки.": "Nobody has given you apples yet.",
        "Пока ни одного болтика — но всё впереди.": "No bolts yet — but there is more to come.",
        "Вы ещё не привязаны ни к одному нику в рейтинге.": "You are not linked to any rating nickname yet.",
        "Добро пожаловать в личный кабинет, воин Пламени.": "Welcome to your cabinet, warrior of the Flame.",
        "Каждый золотой болт — это участие в ивенте союза.": "Every golden bolt is participation in an alliance event.",
        "Доказательство того, что тебе не всё равно.": "Proof that you care.",
        "Суммарная ценность ресурсов": "Total resource value",
        "Купоны героя": "Hero coupons",
        "Общие детали": "Common parts",
        "Клетки титана": "Titan cells",
        "Точные чертежи": "Precise blueprints",
        "Биогенный белок": "Biogenic protein",
        "Молот перековки": "Reforging hammer",
        "Изолента для перековки": "Reforging tape",
        "Ускорения": "Speedups",
        "Ускорения общие": "General speedups",
        "Ускорения тренировки": "Training speedups",
        "Ускорения исследований": "Research speedups",
        "Ускорения строительства": "Construction speedups",
        "Сыворотки титана": "Titan serums",
        "Алмазы из наборов": "Diamonds from packs",
        "Руководства по навыкам героя": "Hero skill guides",
        "Фрагменты редкого героя": "Rare hero fragments",
        "Фрагменты эпического героя": "Epic hero fragments",
        "Фрагменты легендарного героя": "Legendary hero fragments",
        "Фрагменты снаряжения": "Equipment fragments",
        "Нужно фрагментов": "Fragments needed",
        "Нужно фрагментов героев": "Hero fragments needed",
        "Нужно фрагментов снаряжения": "Equipment fragments needed",
        "Нужно клеток титана": "Titan cells needed",
        "Всего нужно книг": "Total books needed",
        "Осталось подарить на этой неделе:": "Left to gift this week:",
        "Снаряжение": "Equipment",
        "Эксклюзивное снаряжение": "Exclusive equipment",
        "Усиление снаряжения (сплав)": "Equipment enhancement (alloy)",
        "Усиление легендарного снаряжения": "Legendary equipment enhancement",
        "Звёзды легендарных героев": "Legendary hero stars",
        "Прокачка с 0 по 10 звёзд": "Upgrade from 0 to 10 stars",
        "Прокачка с 1 по 15 уровень": "Upgrade from level 1 to 15",
        "Текущее количество звёзд": "Current star count",
        "Желаемое количество звёзд": "Desired star count",
        "Текущая звезда": "Current star",
        "Желаемая звезда": "Desired star",
        "Текущий лепесток (1–6)": "Current petal (1–6)",
        "Введите текущую звезду и лепесток, а также желаемое количество звёзд (1–10)": "Enter the current star and petal, plus the desired star count (1–10)",
        "Введите текущую звезду и лепесток, а также желаемое количество звёзд (1–60)": "Enter the current star and petal, plus the desired star count (1–60)",
        "Введите текущий и желаемый уровень каждого навыка (1–40)": "Enter the current and desired level of each skill (1–40)",
        "Нужно фрагментов героев": "Hero fragments needed",
        "Жетоны продвинутого призыва": "Advanced summon tokens",
        "Жетоны стандартного призыва": "Standard summon tokens",
        "Обломки снаряжения (100 опыта)": "Equipment scraps (100 XP)",
        "Обломки снаряжения (400 опыта)": "Equipment scraps (400 XP)",
        "Обломки снаряжения (2 000 опыта)": "Equipment scraps (2,000 XP)",
        "Обломки снаряжения (10 000 опыта)": "Equipment scraps (10,000 XP)",
        "Все калькуляторы — черепашка и прокачка": "All calculators — Turtle and upgrades",
        "— данные вносятся в минутах": "— values are entered in minutes",
        "— учтен бафф VIP 10 (6 солдатиков в минуту)": "— includes the VIP 10 buff (6 soldiers per minute)",
        "дают удвоенные очки.": "give double points.",
        "Результаты могут отличаться в зависимости от уровня VIP игрока. Параметры с плашкой": "Results may vary depending on the player's VIP level. Parameters marked with",
        "Выберите ранг, чтобы увидеть, как будет выглядеть кабинет. Данные (место, очки) остаются реальными.": "Choose a rank to preview the cabinet. Data (place, points) stays real.",
        "⚠ ПРОСМОТР ОФОРМЛЕНИЯ — данные не реальные": "⚠ APPEARANCE PREVIEW — data is not real",
        "Введите мощь каждого отряда. Формат ввода:": "Enter each squad's power. Input format:",
        "Сохраняется в виде": "Saved as",
        "1 отряд": "Squad 1",
        "2 отряд": "Squad 2",
        "3 отряд": "Squad 3",
        "4 отряд": "Squad 4",
        "5 отряд": "Squad 5",
        "Боевая мощь отрядов": "Squad combat power",
        "⚔ Боевая мощь отрядов": "⚔ Squad combat power",
        "Вклад в общий рейтинг:": "Contribution to overall rating:",
        "Можно обновлять в любой момент": "Can be updated at any time",
        "Пустое поле — допустимо.": "An empty field is allowed.",
        ". Пустое поле — допустимо.": "An empty field is allowed.",
        "Просмотреть оформление": "Preview appearance",
        "👁 Просмотреть оформление": "👁 Preview appearance",
        "Сохранить мощь отрядов": "Save squad power",
        "💾 Сохранить мощь отрядов": "💾 Save squad power",
        "Мой график — Дуэль": "My chart — Duel",
        "📈 Мой график — Дуэль": "📈 My chart — Duel",
        "Мой график — Аркадия": "My chart — Arcadia",
        "📈 Мой график — Аркадия": "📈 My chart — Arcadia",
        "Яблоки": "Apples",
        "🍎 Яблоки": "🍎 Apples",
        "Золото": "Gold",
        "🥇 Золото": "🥇 Gold",
        "Серебро": "Silver",
        "🥈 Серебро": "🥈 Silver",
        "Бронза": "Bronze",
        "🥉 Бронза": "🥉 Bronze",
        "Камень": "Stone",
        "🪨 Камень": "🪨 Stone",
        "Алмаз": "Diamond",
        "💎 Алмаз": "💎 Diamond",
        "Сталь": "Steel",
        "⚙️ Сталь": "⚙️ Steel",
        "Никнеймы": "Nicknames",
        "Выбор ника": "Nickname selection",
        "Выбор ника | [HEL] Ацкое Пламя": "Nickname selection | [HEL] Ацкое Пламя",
        "Найди свой ник в общем рейтинге и привяжи его к аккаунту.": "Find your nickname in the overall rating and link it to your account.",
        "! Найди свой ник в общем рейтинге и привяжи его к аккаунту.": "! Find your nickname in the overall rating and link it to your account.",
        "Свободных ников в рейтинге пока нет. Обратитесь к администратору.": "There are no free rating nicknames yet. Contact an administrator.",
        "Ранг не определён": "Rank not determined",
        "· место": "· place",
        "Штат | [HEL] Ацкое Пламя": "State | [HEL] Ацкое Пламя",
        "Рейтинг | [HEL] Ацкое Пламя": "Rating | [HEL] Ацкое Пламя",
        "Рейтинг Дуэли | [HEL] Ацкое Пламя": "Duel Rating | [HEL] Ацкое Пламя",
        "Рейтинг Аркадии | [HEL] Ацкое Пламя": "Arcadia Rating | [HEL] Ацкое Пламя",
        "Ивенты | [HEL] Ацкое Пламя": "Events | [HEL] Ацкое Пламя",
        "Калькулятор | [HEL] Ацкое Пламя": "Calculator | [HEL] Ацкое Пламя",
        "Личный кабинет | [HEL] Ацкое Пламя": "Personal cabinet | [HEL] Ацкое Пламя",
        "Регистрация | [HEL] Ацкое Пламя": "Sign up | [HEL] Ацкое Пламя",
        "Прогресс: | [HEL] Ацкое Пламя": "Progress: | [HEL] Ацкое Пламя",
        "Роль": "Role",
        "Заявка на интервью | [HEL] Ацкое Пламя": "Interview application | [HEL] Ацкое Пламя",
        "Заявка на интервью": "Interview application",
        "Хотите вступить в [HEL] или обсудить переход целым союзом? Заполните заявку — мы свяжемся с вами для интервью. Все поля обязательны.": "Want to join [HEL] or discuss moving with your whole alliance? Fill in the application — we will contact you for an interview. All fields are required.",
        "Штат": "State",
        "Союз": "Alliance",
        "Никнейм": "Nickname",
        "Координаты в игре": "In-game coordinates",
        "Текст заявки": "Application text",
        "Дата и время подачи фиксируются автоматически.": "The date and time of submission are recorded automatically.",
        "Отправить заявку": "Submit application",
        "Заявка отправлена": "Application submitted",
        "Спасибо! Мы получили вашу заявку и свяжемся с вами. Дата и время подачи зафиксированы.": "Thank you! We received your application and will contact you. The date and time of submission are recorded.",
        "← Вернуться на главную": "← Back to home",
        "Например: 657": "For example: 657",
        "Название союза": "Alliance name",
        "Ваш игровой ник": "Your in-game nickname",
        "Например: X:512 Y:384": "For example: X:512 Y:384",
        "Расскажите о себе: сила, T10, активность, опыт, состав команды, почему хотите к нам.": "Tell us about yourself: power, T10, activity, experience, team, and why you want to join us.",
        "Подать заявку на интервью": "Apply for an interview",
        "Сделать окном заявки": "Make application slide",
        "Дуэль": "Duel",
        "Аркадия": "Arcadia",
        "БМ": "GB",
        "Очки": "Points",
        "Войдите, чтобы продолжить.": "Please log in to continue.",
        "ТВОЙ ВЫБОР": "YOUR CHOICE",
        "Миграция — редкое и важное событие. Двери нашего штата открываются раз в 1,5 месяца после сброса сезона. Если ты готов к активной игре и хочешь стать частью нашей команды — не упусти момент. Пиши координатору [HEL]Artemida для деталей.": "Migration is a rare and important event. Our state opens its doors once every 1.5 months after a season reset. If you are ready for active play and want to become part of our team, don't miss your chance. Message coordinator [HEL]Artemida for details.",
        "[HEL] — ЭТО СЕРДЦЕ ШТАТА 657": "[HEL] — THE HEART OF STATE 657",
        "Союз основан 4 апреля 2026 года, мы прошли путь от штата 673 до 657-го. Здесь собираются игроки, которые ценят динамику, командный дух и стабильный результат. Мы играем, чтобы побеждать, и побеждаем, чтобы играть вместе.": "The alliance was founded on April 4, 2026. We have come a long way from state 673 to 657. Here gather players who value momentum, team spirit and steady results. We play to win, and we win to play together.",
        "ГУБЕРНАТОРСТВО": "GOVERNORSHIP",
        "[HEL] - губернатор штата 657. Титулы раздаются по запросу: кто первый попросил, тот получил. Баффы запускаем накануне вечером. Тренировка для черепашки - в понедельник. Системы раздачи сундуков за захват Аркадии нет - слишком несущественно для лишних заморочек.": "[HEL] is the governor of state 657. Titles are given on request: first come, first served. Buffs are activated the evening before. Turtle training is on Monday. There is no chest reward system for capturing Arcadia — it is too minor to bother with.",
        "[HEL] — ЭТО ПРИНЦИПЫ": "[HEL] — THESE ARE OUR PRINCIPLES",
        "Раньше в 657 было множество запретов и ограничений. Нам претит такой подход, мы отменили все правила. Здесь нет тотального контроля. Ты буквально делаешь то, что хочешь и когда хочешь, а рыночный инструмент оценки – реакция от окружающих, сама тебя направит": "State 657 used to be full of bans and restrictions. We dislike that approach, so we abolished all the rules. There is no total control here. You literally do what you want, when you want, and the market-like feedback from others will guide you.",
        "ПОБЕЖДАЕТ СИЛЬНЕЙШИЙ": "THE STRONGEST WINS",
        "Мы не вмешиваемся в регулирование там, где всё решается конкуренцией и рыночными методами — как внутри союза, так и между союзами. Наша политика — лояльность к активным игрокам и честная борьба. Побеждает сильнейший.": "We do not interfere where competition and market forces decide — both inside the alliance and between alliances. Our policy is loyalty to active players and fair play. The strongest wins.",
        "ЭКОСИСТЕМА HEL": "THE HEL ECOSYSTEM",
        "В нашем штате каждый найдет свой темп игры. Хочешь хардкорных замесов — тебе в HEL. Предпочитаешь спокойную игру и общение — мы как раз в поиске второго союза, формируем свою экосистему из двух союзов. Примем в свои ряды как сплоченные команды, так и одиноких воинов.": "Everyone can find their own pace in our state. Want hardcore battles? Join HEL. Prefer a calmer game and good company? We are looking for a second alliance and building our own two-alliance ecosystem. We welcome both tight teams and lone warriors.",
        "ПРИГЛАШАЕМ СОЮЗ!": "ALLIANCE WANTED!",
        "Условия сотрудничества просты: HEL обеспечивает ежесезонную ротацию во второй союз, повышая активность, а второй союз поддерживает HEL, например, если в HEL останутся пустые места накануне перед аркадией или дуэлью мы переместим часть игроков в HEL для достижения победы.": "The terms are simple: HEL provides seasonal rotation to the second alliance, boosting activity, while the second alliance supports HEL. For example, if HEL has empty slots before Arcadia or a duel, we move some players to HEL to secure the win.",
        "РОТАЦИЯ - ПУТЬ К ПОБЕДЕ": "ROTATION IS THE PATH TO VICTORY",
        "Это не просто инструмент самообновления, а забота о качестве игры. Каждый сезон мы анализируем активность, кто хочет большего, переходят в топ. Те, кто берет паузу — в союз с комфортным темпом. Это позволяет нам сохранять высокий темп и давать игрокам подходящую нагрузку.": "This is not just a self-renewal tool, but care for the quality of the game. Every season we review activity: those who want more move up. Those taking a break join an alliance with a comfortable pace. This lets us keep a high tempo and give players the right workload.",
        "РЕЙТИНГОВАЯ СИСТЕМА": "RATING SYSTEM",
        "Рейтинги нужны, чтобы каждый видел свой вклад и понимал, что его время реально двигает союз к победе. Без них активные остаются незамеченными. Прозрачная система — это уважение к тем, кто играет. Мы снимаем статистику чтобы знать свои силы": "Ratings let everyone see their contribution and understand that their time really moves the alliance toward victory. Without them, active players go unnoticed. A transparent system is respect for those who play. We track statistics to know our strength.",
        "ИММУНИТЕТ ОТ РОТАЦИИ": "IMMUNITY FROM ROTATION",
        "В нашей рейтинговой системе есть место человечности. На сайте дарим друг другу яблоки — каждую неделю по пять штук любому участнику союза. Топ-10 игроков по сбору яблок получают иммунитет от ротации, безотносительно результатов дуэли и лиги. Иногда важнее не очки, а поддержка.": "There is room for humanity in our rating system. On the site we give each other apples — five per week to any alliance member. The top 10 apple collectors receive immunity from rotation, regardless of duel and league results. Sometimes support matters more than points.",
        "ДУЭЛЬ СОЮЗОВ": "ALLIANCE DUEL",
        "Рейтинг дуэли — это способ подсветить тех, кто играет каждый день и выкладывается в каждом заходе. Он честно отражает вклад каждого в общий результат, независимо от прокачки и доната, и даёт равные шансы заявить о себе. Так союз понимает, на кого можно опереться.": "The duel rating highlights those who play every day and give their best in every session. It fairly reflects each player's contribution to the common result, regardless of upgrades or donations, and gives everyone an equal chance to prove themselves. This is how the alliance knows who it can rely on.",
        "АРКАДИЯ": "ARCADIA",
        "Аркадия — это ивент, где решает военная мощь. Рейтинг Аркадии показывает, кто реально вложился в захват и принёс союзу победу, а не просто отсиделся в стороне. В нём виден вклад каждого бойца — от топов до тех, кто только набирает силу, но уже играет на результат.": "Arcadia is an event where military power decides. The Arcadia rating shows who really invested in the capture and brought the alliance victory instead of sitting it out. It reveals every fighter's contribution — from the top players to those still growing but already playing for the result.",
        "ЗОЛОТОЙ БОЛТ": "GOLDEN BOLT",
        "Также ведем рейтинг участия в союзных ивентах - аналогах нефти, схватки на драконьем острове и меди. Если ты заслужил золотой болт, - значит ты совершил над собой усилие и пришел на помощь команде в нужную минуту. Это прямое доказательство того, что тебе не все равно.": "We also track participation in alliance events such as Oil, Dragon Island battles and Copper. If you earned a golden bolt, you pushed yourself and came to help the team at the right moment. It is direct proof that you care.",
        "[HEL] — ЭТО НАСТОЯЩИЕ ЛЮДИ": "[HEL] — REAL PEOPLE",
        "Наши болячки такие же, как и у всех. Мы не идеальная команда: бывает недопонимание, бывают поражения, бывает, что люди бросают игру. Никто кровью не подписывается при вступлении, что мы тут навсегда и что интересы союза выше собственных.": "We have the same problems as everyone else. We are not a perfect team: misunderstandings happen, defeats happen, people quit. Nobody signs in blood on joining that they will stay forever and put the alliance above themselves.",
        "ПОБЕДЫ НАЧИНАЮТСЯ С МАЛОГО": "VICTORIES START SMALL",
        "Мы ценим вклад каждого игрока на каждом ивенте, не смотря на то, что в рейтинг не идут маленькие события типа льва, участие на нем приветствуется и будет полезно в первую очередь для тебя самого, для роста твоего аккаунта.": "We value every player's contribution at every event. Even though small events like Lion do not count toward the rating, participation is welcome and will benefit you first of all by growing your account.",
        "РАСПИСАНИЕ": "SCHEDULE",
        "Наше расписание — это чёткий план действий. Мы знаем, когда и какой ивент мы играем, и всегда держим команду в курсе. Никаких пропущенных событий: расписание рассылается заранее. Дисциплина и организация — основа наших результатов.": "Our schedule is a clear action plan. We know when and which event we play and always keep the team informed. No missed events: the schedule is sent in advance. Discipline and organization are the foundation of our results.",
        "ПЕРСОНАЛЬНЫЙ \"ШТАБ\"": "YOUR PERSONAL \"HQ\"",
        "Мы не играем вслепую. Специально для нашего штата создан портал с аналитикой. Рейтинги, интерактивная карта штата, удобные калькуляторы. Вся статистика и планирование в одном месте. Играй с умом и преимуществом, планируй свои победы заранее.": "We do not play blind. A dedicated analytics portal was built for our state: ratings, an interactive state map and handy calculators. All statistics and planning in one place. Play smart with an advantage and plan your victories in advance.",
        "ТВОЯ КОМАНДА": "YOUR TEAM",
        "Команда формировалась пол года и продолжает развиваться, в наших рядах представители более чем из 10 союзов. Союз на 100% русскоязычный, организованы чаты в Вк, в Телеграме. Первоклассно бросаем кубик в чате игры.": "The team took half a year to form and keeps growing; our ranks include members from more than 10 alliances. The alliance is 100% Russian-speaking, with chats on VK and Telegram. And we roll the dice in the game chat like pros.",
        "КОМАНДНАЯ РАБОТА РЕШАЕТ": "TEAMWORK DECIDES",
        "В 3 сезоне обстоятельства сложились так, что нас осталось 70 человек на старте. Но даже из этой ситуации мы нашли выход: 75% игроков открыли Т10. Даже так мы отыграли две лиги дуэлей с одним поражением. Это в очередной раз демонстрирует важность командной работы и грамотного управления.": "In season 3 circumstances left us with only 70 people at the start. Even so, we found a way: 75% of players unlocked T10. We played two duel leagues with just one defeat. Once again, this shows the importance of teamwork and smart management.",
        "ИГРА, В КОТОРУЮ ХОЧЕТСЯ ВОЗВРАЩАТЬСЯ": "A GAME YOU WANT TO RETURN TO",
        "Наша цель — это получение удовольствия от процесса и от совместных достижений команды. Мы верим, что лучший результат рождается там, где людям комфортно и интересно.": "Our goal is to enjoy the process and the team's shared achievements. We believe the best results are born where people feel comfortable and engaged."
    };

    const patterns = [
        [/^Привет,\s*$/, "Hello, "],
        [/^Дарителей:\s*(.+)$/, "Givers: $1"],
        [/^Всего очков\s*(.+)$/, "Total points: $1"],
        [/^Место в общем\s*(.+)$/, "Overall place: $1"],
        [/^Выбрано строк:\s*(.+)$/, "Rows selected: $1"],
        [/^Дата обновления:\s*(.+)$/, "Updated: $1"],
        [/^Осталось подарить на этой неделе:\s*(.+)$/, "Left to gift this week: $1"],
        [/^Подарили вам за сезон:\s*(.+)$/, "Gifted to you this season: $1"],
        [/^Вклад в общий рейтинг:\s*(.+)$/, "Contribution to overall rating: $1"],
        [/^Сезон\s+(s[1-4])\s*·\s*новая пустая карта$/, "Season $1 · new blank map"],
        [/^Сезон\s+(s[1-4])\s*·\s*сохранённая карта\s*#(\d+)$/, "Season $1 · saved map #$2"],
        [/^(\d+)\s*золотых болтиков?$/, "$1 golden bolts"],
        [/^Дарителей:\s*(\d+)$/, "Givers: $1"]
    ];

    const months = {
        'января': 'January', 'февраля': 'February', 'марта': 'March',
        'апреля': 'April', 'мая': 'May', 'июня': 'June', 'июля': 'July',
        'августа': 'August', 'сентября': 'September', 'октября': 'October',
        'ноября': 'November', 'декабря': 'December'
    };

    function normalize(text) {
        return String(text).replace(/\s+/g, ' ').trim();
    }

    function translate(text) {
        if (!text || !/[\u0400-\u04FF]/.test(text)) return null;
        const norm = normalize(text);
        if (!norm) return null;
        if (Object.prototype.hasOwnProperty.call(EN, norm)) return EN[norm];
        const upper = norm.toUpperCase();
        if (upper !== norm && Object.prototype.hasOwnProperty.call(EN, upper)) return EN[upper];
        for (const [re, replacement] of patterns) {
            if (re.test(norm)) return norm.replace(re, replacement);
        }
        return null;
    }

    function translateMonths(text) {
        return text.replace(/\b(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\b/g,
            m => months[m] || m);
    }

    function translateTextNode(node) {
        const parent = node.parentElement;
        if (!parent) return;
        if (parent.closest('script, style, code, pre, textarea, .lang-switch, [data-no-i18n]')) return;
        const original = node.nodeValue;
        const translated = translate(original);
        if (translated !== null) {
            const leading = original.match(/^\s*/)[0];
            const trailing = original.match(/\s*$/)[0];
            node.nodeValue = leading + translated + trailing;
            return;
        }
        if (/[А-Яа-яЁё]/.test(original)) {
            const withMonths = translateMonths(original);
            if (withMonths !== original) node.nodeValue = withMonths;
        }
    }

    function translateAttributes(el) {
        if (el.closest('.lang-switch, [data-no-i18n]')) return;
        ['placeholder', 'title', 'aria-label', 'alt'].forEach(attr => {
            if (!el.hasAttribute(attr)) return;
            const value = el.getAttribute(attr);
            const translated = translate(value);
            if (translated !== null) el.setAttribute(attr, translated);
        });
    }

    function translateDom(root) {
        if (!root) return;
        if (root.nodeType === Node.TEXT_NODE) {
            translateTextNode(root);
            return;
        }
        if (root.nodeType !== Node.ELEMENT_NODE && root.nodeType !== Node.DOCUMENT_NODE) return;
        if (root.nodeType === Node.ELEMENT_NODE) translateAttributes(root);
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT, {
            acceptNode(node) {
                if (node.nodeType === Node.ELEMENT_NODE) {
                    if (node.matches('script, style, code, pre, textarea, .lang-switch, [data-no-i18n]')) {
                        return NodeFilter.FILTER_REJECT;
                    }
                    translateAttributes(node);
                    return NodeFilter.FILTER_SKIP;
                }
                return NodeFilter.FILTER_ACCEPT;
            }
        });
        while (walker.nextNode()) translateTextNode(walker.currentNode);
    }

    function translateTitle() {
        if (!document.title) return;
        const parts = document.title.split('|');
        const head = translate(parts[0]);
        if (head !== null) parts[0] = ' ' + head + ' ';
        document.title = parts.join('|');
    }

    function run() {
        translateDom(document.body);
        translateTitle();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', run, {once: true});
    } else {
        run();
    }

    let scheduled = false;
    const observer = new MutationObserver(() => {
        if (scheduled) return;
        scheduled = true;
        requestAnimationFrame(() => {
            scheduled = false;
            translateDom(document.body);
        });
    });
    observer.observe(document.body, {childList: true, subtree: true, characterData: true});
})();
