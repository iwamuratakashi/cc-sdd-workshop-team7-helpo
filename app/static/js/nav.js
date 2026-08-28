/**
 * header-navigation-menu モックアップ実装
 *
 * 各画面共通のヘッダーメニューを #app-header 要素に描画する。
 * ログイン状態・ロールは localStorage で画面間共有する（本番実装では
 * local-user-authentication が current_user を解決する想定）。
 */
(function () {
  'use strict';

  var STORAGE_KEY = 'helpo_mock_current_user';

  // 3リンク固定。非活性でも非表示にはしない。
  var NAV_LINKS_CONFIG = [
    { key: 'question', href: '/chat', label: '質問' },
    { key: 'history', href: '/history', label: '履歴' },
    { key: 'faq_admin', href: '/faqs/upload', label: 'FAQ管理' }
  ];

  var ROLE_LABELS = {
    user: '一般利用者',
    admin: '管理者'
  };

  // ===== 現在利用者の取得 =====
  function getCurrentMockUser() {
    try {
      var raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        return null;
      }
      var parsed = JSON.parse(raw);
      if (!parsed || !parsed.username || !parsed.role) {
        return null;
      }
      return parsed;
    } catch (e) {
      return null;
    }
  }

  function setCurrentMockUser(username, role) {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ username: username, role: role }));
  }

  function clearCurrentMockUser() {
    window.localStorage.removeItem(STORAGE_KEY);
  }

  // ===== 活性/非活性判定 =====
  function buildHeaderMenuContext(currentUser) {
    var isLoggedIn = !!currentUser;
    var isAdmin = isLoggedIn && currentUser.role === 'admin';

    var links = NAV_LINKS_CONFIG.map(function (link) {
      var active;
      if (link.key === 'faq_admin') {
        active = isAdmin;
      } else {
        active = isLoggedIn;
      }
      return {
        key: link.key,
        href: link.href,
        label: link.label,
        active: active
      };
    });

    return {
      links: links,
      showUserInfo: isLoggedIn,
      showLogout: isLoggedIn,
      username: isLoggedIn ? currentUser.username : null,
      role: isLoggedIn ? currentUser.role : null
    };
  }

  // ===== ログアウト操作 =====
  function mockLogout() {
    clearCurrentMockUser();
    window.location.href = '/login';
  }
  window.mockLogout = mockLogout;

  // ===== 描画 =====
  function escapeHtml(str) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  function renderHeaderMenu(container, context) {
    var linksHtml = context.links.map(function (link) {
      if (link.active) {
        return '<a class="hnm-link" href="' + link.href + '">' + escapeHtml(link.label) + '</a>';
      }
      return '<span class="hnm-link hnm-link-inactive" aria-disabled="true" tabindex="-1">' + escapeHtml(link.label) + '</span>';
    }).join('');

    var userInfoHtml = '';
    if (context.showUserInfo) {
      var roleLabel = ROLE_LABELS[context.role] || context.role;
      userInfoHtml = '<span class="hnm-user">' + escapeHtml(context.username) + '（' + escapeHtml(roleLabel) + '）</span>';
    }

    var logoutHtml = '';
    if (context.showLogout) {
      logoutHtml = '<button type="button" class="hnm-logout" onclick="mockLogout()">ログアウト</button>';
    }

    container.innerHTML =
      '<div class="hnm-inner">' +
        '<span class="hnm-title" role="presentation">HELPO</span>' +
        '<nav class="hnm-links">' + linksHtml + '</nav>' +
        '<div class="hnm-account">' + userInfoHtml + logoutHtml + '</div>' +
      '</div>';
  }

  // ===== 共通CSSの注入 =====
  function ensureStyles() {
    if (document.getElementById('hnm-styles')) {
      return;
    }
    var style = document.createElement('style');
    style.id = 'hnm-styles';
    style.textContent =
      '.hnm-inner{display:flex;align-items:center;gap:24px;flex-wrap:wrap;}' +
      '.hnm-title{font-size:18px;font-weight:700;letter-spacing:0.03em;color:#fff;cursor:default;user-select:none;}' +
      '.hnm-links{display:flex;gap:16px;flex:1;flex-wrap:wrap;}' +
      '.hnm-link{color:#fff;font-size:14px;font-weight:600;text-decoration:none;opacity:0.95;}' +
      '.hnm-link:hover{text-decoration:underline;}' +
      '.hnm-link-inactive{color:rgba(255,255,255,0.5);cursor:not-allowed;pointer-events:none;text-decoration:none;}' +
      '.hnm-account{display:flex;align-items:center;gap:12px;}' +
      '.hnm-user{color:#fff;font-size:13px;opacity:0.9;white-space:nowrap;}' +
      '.hnm-logout{font-size:13px;font-weight:600;color:#2563eb;background:#fff;border:none;border-radius:6px;padding:6px 14px;cursor:pointer;}' +
      '.hnm-logout:hover{background:#e5e7eb;}';
    document.head.appendChild(style);
  }

  function initHeaderMenu() {
    var container = document.getElementById('app-header');
    if (!container) {
      return;
    }
    ensureStyles();
    var currentUser = getCurrentMockUser();
    var context = buildHeaderMenuContext(currentUser);
    renderHeaderMenu(container, context);
  }

  window.HeaderNavigationMenu = {
    getCurrentMockUser: getCurrentMockUser,
    setCurrentMockUser: setCurrentMockUser,
    clearCurrentMockUser: clearCurrentMockUser,
    buildHeaderMenuContext: buildHeaderMenuContext,
    init: initHeaderMenu
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initHeaderMenu);
  } else {
    initHeaderMenu();
  }
})();
