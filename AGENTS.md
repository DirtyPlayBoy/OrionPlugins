# OrionPlugins — карта для ИИ-агентов

Цель: **минимум токенов, максимум точности** при написании плагинов Orion.

## Что такое плагин

Отдельный процесс + `plugin.toml` + JSON-RPC на loopback. Не скрипт внутри UI.

## Быстрый старт

1. Спроси у пользователя: что делает плагин, id/name/author/license, абсолютный путь папки.
2. Scaffold: `python cli/orion_plugin.py new <name> --dir <abs-path> --author "..."`
   или скопируй `examples/dice-roller`.
3. SDK: `pip install -e sdk/python`
4. Проверка: `python cli/orion_plugin.py check <folder>`
5. В Orion: **Плагины → Разработка** → режим разработчика → Загрузить папку.

## Контракт (MVP)

- Ready-строка за ≤20 с: `ORION_PLUGIN_READY port=<n>`
- RPC: `health_check`, `shutdown`, `list_tools`, `call_tool`
- Header: `x-plugin-token` == `--auth-token`
- Args от хоста: `--host-addr`, `--plugin-id`, `--auth-token` (`--daemon-addr` = alias)

## Capabilities (boolean)

`tools` (основной MVP), `tts`, `stt`, `ai_provider`, `client`, `actions`, `triggers`,
`ui_contributions`, `event_handlers`, `dom_access`. Неизвестные ключи — ошибка manifest.

## Документы

| Язык | Старт |
|------|--------|
| EN | `docs/en/getting-started.md` |
| RU | `docs/ru/getting-started.md` |

Канон для агента: этот файл + `docs/*/manifest.md`. Если offline-промпт в приложении спорит с docs — верь docs.

## Каталог

Публикация → PR в https://github.com/DirtyPlayBoy/orion-registry
(байты на GitHub Release автора, реестр только pin digest).
