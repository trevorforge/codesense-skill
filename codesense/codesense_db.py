#!/usr/bin/env python3
"""CodeSense DB Helper — SQLite backend for the CodeSense coding tutor skill."""

import json
import sqlite3
import sys
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "codesense.db"


def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ── Schema ───────────────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS user_profile (
    id INTEGER PRIMARY KEY DEFAULT 1,
    name TEXT DEFAULT 'User',
    overall_level TEXT DEFAULT 'beginner',
    onboarding_complete INTEGER DEFAULT 0,
    streak_days INTEGER DEFAULT 0,
    last_session_date TEXT,
    total_sessions INTEGER DEFAULT 0,
    total_xp INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS domains (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    sort_order INTEGER,
    icon TEXT
);

CREATE TABLE IF NOT EXISTS concepts (
    id INTEGER PRIMARY KEY,
    domain_id INTEGER REFERENCES domains(id),
    term TEXT UNIQUE,
    simple_definition TEXT,
    analogy TEXT,
    detailed_definition TEXT,
    advanced_definition TEXT,
    example TEXT,
    difficulty_tier INTEGER DEFAULT 1,
    prerequisites TEXT DEFAULT '[]',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS progress (
    id INTEGER PRIMARY KEY,
    concept_id INTEGER UNIQUE REFERENCES concepts(id),
    confidence REAL DEFAULT 0.0,
    explanation_level INTEGER DEFAULT 1,
    times_seen INTEGER DEFAULT 0,
    times_correct INTEGER DEFAULT 0,
    times_wrong INTEGER DEFAULT 0,
    last_reviewed TEXT,
    next_review TEXT,
    ease_factor REAL DEFAULT 2.5,
    interval_days REAL DEFAULT 0.0,
    streak INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS skill_tree (
    id INTEGER PRIMARY KEY,
    domain_id INTEGER REFERENCES domains(id),
    level INTEGER DEFAULT 0,
    xp_earned INTEGER DEFAULT 0,
    xp_required INTEGER DEFAULT 100,
    unlocked INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY,
    type TEXT,
    started_at TEXT DEFAULT (datetime('now')),
    ended_at TEXT,
    questions_asked INTEGER DEFAULT 0,
    questions_correct INTEGER DEFAULT 0,
    concepts_touched TEXT DEFAULT '[]'
);
"""

# ── Seed Data ────────────────────────────────────────────────────────────────

SEED_DOMAINS = [
    (1, "How the Internet Works", 1, "🌐"),
    (2, "HTML", 2, "📄"),
    (3, "CSS", 3, "🎨"),
    (4, "JavaScript Basics", 4, "⚡"),
    (5, "The Terminal", 5, "💻"),
    (6, "Dev Tools & Workflow", 6, "🔧"),
    (7, "How Web Apps Work", 7, "🏗"),
    (8, "Modern Frameworks", 8, "📦"),
    (9, "Git & Version Control", 9, "🌿"),
    (10, "Node.js & npm", 10, "📗"),
]

SEED_CONCEPTS = [
    # Domain 1: How the Internet Works
    {
        "domain_id": 1, "term": "URL",
        "simple_definition": "A URL is just an address for a webpage, like a street address for a house. It tells your browser exactly where to go.",
        "analogy": "A URL is like a GPS coordinate. Just as GPS coordinates pinpoint an exact location on Earth, a URL pinpoints an exact page on the internet.",
        "detailed_definition": "A Uniform Resource Locator (URL) is a reference to a web resource that specifies its location and how to retrieve it. It consists of a protocol (http/https), domain name, and optional path, query parameters, and fragment.",
        "advanced_definition": "URLs follow RFC 3986 syntax: scheme://authority/path?query#fragment. The authority includes optional userinfo@, host, and :port. Percent-encoding handles reserved characters. Relative URLs resolve against a base URL.",
        "example": "https://www.example.com/blog/my-post?sort=newest#comments\n\nhttps://  = protocol (secure)\nwww.example.com = domain (the server)\n/blog/my-post = path (which page)\n?sort=newest = query (extra instructions)\n#comments = fragment (scroll to this section)",
        "difficulty_tier": 1, "prerequisites": "[]"
    },
    {
        "domain_id": 1, "term": "HTTP",
        "simple_definition": "HTTP is the language browsers and servers use to talk to each other. Your browser asks for a page, the server sends it back.",
        "analogy": "HTTP is like ordering at a restaurant. You (the browser) ask the waiter (HTTP) for a dish (webpage). The waiter takes your order to the kitchen (server), and brings back your food (the page).",
        "detailed_definition": "HyperText Transfer Protocol is the application-layer protocol for transmitting hypermedia documents. It follows a request-response model: the client sends a request with a method (GET, POST, etc.), headers, and optional body; the server responds with a status code, headers, and body.",
        "advanced_definition": "HTTP/1.1 uses persistent connections by default. HTTP/2 introduces multiplexing, header compression (HPACK), and server push over a single TCP connection. HTTP/3 replaces TCP with QUIC for reduced latency. Methods are idempotent (GET, PUT, DELETE) or non-idempotent (POST).",
        "example": "When you type a URL and hit Enter:\n1. Browser sends: GET /index.html HTTP/1.1\n2. Server responds: HTTP/1.1 200 OK (here's the page)\n\nCommon status codes:\n200 = Success\n404 = Not Found\n500 = Server Error",
        "difficulty_tier": 1, "prerequisites": '["URL"]'
    },
    {
        "domain_id": 1, "term": "DNS",
        "simple_definition": "DNS is the internet's phone book. It translates website names (like google.com) into the actual number-addresses that computers use to find each other.",
        "analogy": "DNS is like your phone's contact list. You tap 'Mom' instead of dialing 555-0123. DNS lets you type 'google.com' instead of '142.250.80.46'.",
        "detailed_definition": "The Domain Name System is a hierarchical naming system that resolves human-readable domain names to IP addresses. It uses a distributed database of name servers organized in a tree: root servers, TLD servers (.com, .org), and authoritative servers for specific domains.",
        "advanced_definition": "DNS resolution involves recursive and iterative queries through the resolver chain. Records include A (IPv4), AAAA (IPv6), CNAME (alias), MX (mail), TXT (verification), NS (nameserver), and SOA (zone authority). TTL controls caching. DNSSEC adds cryptographic authentication.",
        "example": "You type: google.com\n\n1. Browser checks its cache\n2. Asks your router\n3. Router asks your ISP's DNS server\n4. DNS server looks up google.com → 142.250.80.46\n5. Browser connects to that IP address",
        "difficulty_tier": 1, "prerequisites": '["URL"]'
    },
    {
        "domain_id": 1, "term": "server",
        "simple_definition": "A server is just a computer that's always on, waiting to send you stuff when you ask for it. When you visit a website, a server sends you that page.",
        "analogy": "A server is like a librarian. You walk up and ask for a book (webpage). The librarian finds it on the shelf (storage) and hands it to you. They serve many people all day long.",
        "detailed_definition": "A server is a computer or program that provides services to other programs or devices (clients). Web servers specifically handle HTTP requests, serving files, running application logic, and communicating with databases. Common web servers include Nginx and Apache.",
        "advanced_definition": "Servers handle concurrent connections through event loops (Node.js, Nginx) or thread/process pools (Apache prefork). They can serve static files directly or proxy to application servers. Reverse proxies, load balancers, and CDNs form the serving infrastructure. Containers (Docker) and orchestration (Kubernetes) manage deployment.",
        "example": "Your computer (client) asks: 'Give me the homepage'\nThe server responds: 'Here it is!' and sends HTML, CSS, images\n\nWebflow has servers that store your site and send it to visitors.",
        "difficulty_tier": 1, "prerequisites": '["HTTP"]'
    },
    {
        "domain_id": 1, "term": "client vs server",
        "simple_definition": "The client is your browser (the thing asking for stuff). The server is the computer far away that sends stuff back. Every website interaction is this back-and-forth.",
        "analogy": "It's like a drive-through. You (client) pull up and say what you want into the speaker. The kitchen (server) makes it and hands it through the window. You never go into the kitchen.",
        "detailed_definition": "The client-server model divides work between service requesters (clients) and service providers (servers). In web development, the browser is the client that renders HTML/CSS and runs JavaScript. The server handles data storage, authentication, business logic, and serves responses.",
        "advanced_definition": "Modern architectures blur the line: SSR (server-side rendering) generates HTML on the server, while SPAs (single-page apps) shift rendering to the client. Hybrid approaches like Next.js use both. Edge computing moves server logic closer to clients. WebSockets enable bidirectional communication beyond simple request-response.",
        "example": "Client-side (your browser):\n- Displays the page\n- Handles clicks and animations\n- Runs JavaScript locally\n\nServer-side (remote computer):\n- Stores the data\n- Processes logins\n- Sends pages when asked",
        "difficulty_tier": 1, "prerequisites": '["server", "HTTP"]'
    },
    {
        "domain_id": 1, "term": "IP address",
        "simple_definition": "An IP address is a unique number that identifies every device on the internet. It's how computers find each other, like a home address for your computer.",
        "analogy": "If the internet is a city, an IP address is a street address. Every building (computer/server) has one so mail (data) can be delivered to the right place.",
        "detailed_definition": "An Internet Protocol address is a numerical label assigned to each device on a network. IPv4 uses 32-bit addresses (e.g., 192.168.1.1) while IPv6 uses 128-bit addresses. Public IPs are globally unique; private IPs (like 192.168.x.x) are used within local networks and translated via NAT.",
        "advanced_definition": "IPv4 exhaustion drove IPv6 adoption (128-bit, 3.4x10^38 addresses). Subnetting uses CIDR notation (e.g., 10.0.0.0/8). NAT maps private to public IPs. DHCP assigns IPs dynamically. Anycast routes to the nearest server sharing an IP. BGP handles inter-AS routing of IP prefixes.",
        "example": "IPv4: 192.168.1.1 (four numbers, 0-255 each)\nIPv6: 2001:0db8:85a3::8a2e:0370:7334\n\nYour home network: 192.168.x.x (private)\nGoogle's server: 142.250.80.46 (public)",
        "difficulty_tier": 1, "prerequisites": "[]"
    },
    # Domain 2: HTML
    {
        "domain_id": 2, "term": "HTML",
        "simple_definition": "HTML is the skeleton of every webpage. It defines the structure: what's a heading, what's a paragraph, what's a link. It's not about how things look, just what things ARE.",
        "analogy": "HTML is like the blueprint of a house. It says 'here's the living room, here's the kitchen, here's a door.' It doesn't pick paint colors or furniture (that's CSS). It just defines the rooms.",
        "detailed_definition": "HyperText Markup Language is the standard markup language for creating web pages. It uses a system of nested tags (elements) to define the document structure. Browsers parse HTML into a DOM (Document Object Model) tree, which is then rendered visually.",
        "advanced_definition": "HTML5 introduced semantic elements, native audio/video, canvas, Web Storage, Web Workers, and numerous APIs. The parser follows the WHATWG Living Standard with specific error-recovery rules. The DOM is a tree of Node objects exposing an API for JavaScript manipulation.",
        "example": "<h1>This is a heading</h1>\n<p>This is a paragraph.</p>\n<a href=\"https://example.com\">This is a link</a>\n<img src=\"photo.jpg\" alt=\"A photo\">\n\nEach tag tells the browser WHAT something is.",
        "difficulty_tier": 1, "prerequisites": "[]"
    },
    {
        "domain_id": 2, "term": "HTML element",
        "simple_definition": "An element is a single building block in HTML. It has an opening tag, some content, and a closing tag. Like <p>Hello</p> is one element that makes a paragraph.",
        "analogy": "An HTML element is like a labeled container. The tags are the label ('this is a paragraph'), and the content is what's inside the container ('Hello'). You stack and nest containers to build a page.",
        "detailed_definition": "An HTML element consists of a start tag, content, and end tag. Some elements are void (self-closing) like <img> and <br>. Elements can contain text, other elements, or both. Each element can have attributes that modify its behavior or appearance.",
        "advanced_definition": "Elements map to DOM interfaces (HTMLParagraphElement, HTMLDivElement, etc.). Custom elements can be defined via the Web Components API (customElements.define). Shadow DOM encapsulates element internals. The content model (flow, phrasing, embedded, etc.) defines which elements can nest inside others.",
        "example": "<p>This is a paragraph element</p>\n ^                            ^\n start tag    content      end tag\n\n<img src=\"cat.jpg\" alt=\"A cat\">  ← void element (no end tag)\n\n<div>\n  <h2>Nested elements</h2>\n  <p>A paragraph inside a div</p>\n</div>",
        "difficulty_tier": 1, "prerequisites": '["HTML"]'
    },
    {
        "domain_id": 2, "term": "HTML attribute",
        "simple_definition": "Attributes are extra info you add to an HTML tag to change how it works. Like adding src to an image tag tells it WHICH image to show.",
        "analogy": "If an HTML tag is an order form, attributes are the fields you fill in. The <img> tag says 'I need an image' and the src attribute says 'here's which image file.'",
        "detailed_definition": "HTML attributes provide additional information about elements, specified in the start tag as name-value pairs (name=\"value\"). Global attributes (id, class, style, data-*) work on any element. Element-specific attributes (src, href, alt, type) only apply to certain elements.",
        "advanced_definition": "Boolean attributes (disabled, checked, required) are true when present regardless of value. Custom data attributes (data-*) are accessible via element.dataset. ARIA attributes (role, aria-label) enhance accessibility. Attributes are reflected as DOM properties but the mapping isn't always 1:1 (e.g., class attribute vs className property).",
        "example": "<a href=\"https://example.com\" target=\"_blank\">Click me</a>\n\nhref = where the link goes\ntarget = open in new tab\n\n<img src=\"photo.jpg\" alt=\"A sunset\" width=\"300\">\n\nsrc = which image file\nalt = description for screen readers\nwidth = how wide to display it",
        "difficulty_tier": 1, "prerequisites": '["HTML element"]'
    },
    {
        "domain_id": 2, "term": "div",
        "simple_definition": "A div is a generic container in HTML. It doesn't mean anything by itself. It's just a box you can put other stuff in, usually to group things together for styling.",
        "analogy": "A div is like a cardboard box. It has no special purpose on its own, but you put things in it to keep them organized. In Webflow, every container and section you create is basically a div.",
        "detailed_definition": "The <div> element is a generic flow content container with no semantic meaning. It's used to group elements for styling (via CSS classes) or scripting purposes. Before HTML5 semantic elements, divs were used for all structural grouping.",
        "advanced_definition": "Divs are block-level elements (display: block by default). Overuse of divs ('div soup') indicates poor semantic structure. Prefer semantic elements (section, article, nav, aside, header, footer, main) when they convey meaning. Divs remain appropriate for pure layout grouping with no semantic purpose.",
        "example": "<div class=\"card\">\n  <h3>Card Title</h3>\n  <p>Card content goes here</p>\n  <a href=\"#\">Read more</a>\n</div>\n\nThe div groups the heading, paragraph, and link into one 'card'.\nIn Webflow, when you add a Div Block, you're creating one of these.",
        "difficulty_tier": 1, "prerequisites": '["HTML element"]'
    },
    {
        "domain_id": 2, "term": "semantic HTML",
        "simple_definition": "Semantic HTML means using tags that describe what the content IS, not just how it looks. Using <nav> for navigation and <article> for an article instead of generic <div> for everything.",
        "analogy": "Imagine labeling moving boxes: you could write 'stuff' on every box, or you could write 'kitchen,' 'bedroom,' 'bathroom.' Semantic HTML is like the specific labels. It helps everyone (browsers, screen readers, search engines) understand what's inside.",
        "detailed_definition": "Semantic HTML uses elements that convey meaning about their content: <header>, <nav>, <main>, <article>, <section>, <aside>, <footer>, <figure>, <figcaption>, <time>, <mark>, etc. This improves accessibility (screen readers understand page structure), SEO (search engines weight semantic content), and maintainability.",
        "advanced_definition": "Semantic elements create an implicit ARIA landmark map: <nav> maps to role='navigation', <main> to role='main', etc. The document outline algorithm (now deprecated in practice) was meant to derive heading hierarchy from sectioning elements. Microdata and schema.org extend semantics for structured data.",
        "example": "Bad (div soup):\n<div class=\"header\">...</div>\n<div class=\"nav\">...</div>\n<div class=\"content\">...</div>\n\nGood (semantic):\n<header>...</header>\n<nav>...</nav>\n<main>...</main>\n<article>...</article>\n<footer>...</footer>",
        "difficulty_tier": 2, "prerequisites": '["div", "HTML element"]'
    },
    # Domain 3: CSS
    {
        "domain_id": 3, "term": "CSS",
        "simple_definition": "CSS is what makes websites look good. If HTML is the skeleton, CSS is the skin, clothes, and makeup. It controls colors, fonts, spacing, layout, everything visual.",
        "analogy": "CSS is like an interior designer. The architect (HTML) built the rooms, but the designer (CSS) picks the paint colors, furniture placement, lighting, and decorations. Same rooms, totally different feel.",
        "detailed_definition": "Cascading Style Sheets is a stylesheet language that describes the presentation of HTML documents. It controls layout, colors, fonts, spacing, animations, and responsive behavior. The 'cascade' determines which styles win when multiple rules target the same element, based on specificity, source order, and importance.",
        "advanced_definition": "The cascade resolves conflicts through origin (user-agent, author, user), specificity (inline > ID > class > element), and order. The CSSOM (CSS Object Model) parallels the DOM. Modern CSS includes custom properties (variables), container queries, cascade layers (@layer), :has() selector, subgrid, and extensive animation capabilities.",
        "example": "h1 {\n  color: blue;\n  font-size: 32px;\n  margin-bottom: 16px;\n}\n\n.card {\n  background: white;\n  border-radius: 8px;\n  padding: 20px;\n  box-shadow: 0 2px 4px rgba(0,0,0,0.1);\n}\n\nIn Webflow, every style you set in the Style Panel\nbecomes CSS behind the scenes.",
        "difficulty_tier": 1, "prerequisites": '["HTML"]'
    },
    {
        "domain_id": 3, "term": "CSS selector",
        "simple_definition": "A selector is how you tell CSS WHICH elements to style. It's like pointing at something and saying 'make THAT one blue.' You can point at tags, classes, IDs, or combinations.",
        "analogy": "CSS selectors are like a search filter. Just like you'd filter 'all blue shirts, size medium' when shopping, a selector filters 'all paragraphs inside the header with class highlight.'",
        "detailed_definition": "CSS selectors pattern-match against elements in the DOM. Types include: element (p), class (.card), ID (#main), attribute ([type='text']), pseudo-class (:hover, :first-child), pseudo-element (::before), and combinators (descendant space, child >, sibling +, ~). Specificity determines which selector wins.",
        "advanced_definition": "Selector specificity is calculated as (inline, ID, class+attr+pseudo-class, element+pseudo-element). :is() and :where() take the specificity of their most specific argument (:where() is always 0). :has() enables parent selection. Complex selectors combine simple selectors with combinators. The :not() pseudo-class excludes matches.",
        "example": "p { }              /* all paragraphs */\n.card { }          /* elements with class='card' */\n#hero { }          /* the element with id='hero' */\n.card p { }        /* paragraphs INSIDE .card */\n.card:hover { }    /* .card when mouse hovers */\n\nIn Webflow, when you name a class 'Hero Section',\nyou're creating a CSS selector: .hero-section",
        "difficulty_tier": 1, "prerequisites": '["CSS", "HTML element"]'
    },
    {
        "domain_id": 3, "term": "class",
        "simple_definition": "A class is a reusable name you give to HTML elements so you can style them all the same way. Give multiple elements the same class, and they all get the same look.",
        "analogy": "A class is like a uniform. Every student wearing the 'basketball-team' uniform looks the same. In CSS, every element with the class 'card' gets the same styling.",
        "detailed_definition": "The class attribute assigns one or more space-separated class names to an HTML element. In CSS, classes are selected with a dot prefix (.classname). Multiple elements can share a class, and one element can have multiple classes. Classes are the primary mechanism for reusable styling.",
        "advanced_definition": "Classes participate in specificity at the (0,1,0) level. Methodologies like BEM (.block__element--modifier), SMACSS, and utility-first (Tailwind) provide naming conventions. The classList API (add, remove, toggle, contains) manipulates classes in JavaScript. CSS Modules and scoped styles in frameworks prevent class name collisions.",
        "example": "HTML:\n<div class=\"card\">First card</div>\n<div class=\"card\">Second card</div>\n<div class=\"card featured\">Special card</div>\n\nCSS:\n.card { padding: 20px; border: 1px solid gray; }\n.featured { background: gold; }\n\nIn Webflow, every style you create IS a class.",
        "difficulty_tier": 1, "prerequisites": '["CSS selector", "HTML attribute"]'
    },
    {
        "domain_id": 3, "term": "box model",
        "simple_definition": "Every element on a webpage is a box. The box model describes the layers: the content inside, padding around it, a border, and margin pushing other boxes away.",
        "analogy": "Think of a framed picture on a wall. The picture is the content. The matting around the picture is padding. The frame is the border. The space between frames on the wall is margin.",
        "detailed_definition": "The CSS box model defines how element dimensions are calculated. From inside out: content (width/height), padding (space inside the border), border (visible edge), margin (space outside the border). box-sizing: border-box includes padding and border in the width/height calculation, which is more intuitive.",
        "advanced_definition": "The default content-box model adds padding and border to specified dimensions. border-box (universally recommended via *, *::before, *::after { box-sizing: border-box }) includes them. Margin collapsing merges adjacent vertical margins. The visual formatting model determines how boxes are laid out (block, inline, flex, grid formatting contexts).",
        "example": ".card {\n  width: 300px;\n  padding: 20px;    /* space INSIDE the box */\n  border: 2px solid black;\n  margin: 16px;     /* space OUTSIDE the box */\n}\n\n┌─── margin ──────────────────┐\n│ ┌─ border ───────────────┐  │\n│ │ ┌─ padding ──────────┐ │  │\n│ │ │   content (300px)  │ │  │\n│ │ └────────────────────┘ │  │\n│ └────────────────────────┘  │\n└─────────────────────────────┘",
        "difficulty_tier": 1, "prerequisites": '["CSS"]'
    },
    {
        "domain_id": 3, "term": "flexbox",
        "simple_definition": "Flexbox is a CSS layout tool that makes it easy to arrange items in a row or column and control spacing between them. It's the modern way to lay things out.",
        "analogy": "Flexbox is like a shelf organizer. You decide: should items go left-to-right or top-to-bottom? Should they be spaced evenly? Should one item stretch to fill the remaining space? Flexbox handles all of that.",
        "detailed_definition": "CSS Flexible Box Layout distributes space among items in a container. The flex container (display: flex) controls direction (flex-direction), wrapping (flex-wrap), alignment (justify-content, align-items), and gap. Flex items can grow (flex-grow), shrink (flex-shrink), and have a base size (flex-basis).",
        "advanced_definition": "Flexbox operates on a single axis (main axis + cross axis). The flex shorthand combines flex-grow, flex-shrink, and flex-basis. align-self overrides align-items per item. order re-sequences items visually. Flexbox resolves intrinsic sizing through a multi-pass algorithm considering min/max constraints. Nested flex containers enable complex layouts.",
        "example": ".nav {\n  display: flex;\n  justify-content: space-between;  /* spread items out */\n  align-items: center;             /* vertically center */\n  gap: 16px;                       /* space between items */\n}\n\nIn Webflow, when you set an element's Layout to 'Flex',\nyou're using flexbox. All those flex settings map to CSS.",
        "difficulty_tier": 2, "prerequisites": '["CSS", "box model"]'
    },
    {
        "domain_id": 3, "term": "CSS grid",
        "simple_definition": "CSS Grid lets you create two-dimensional layouts with rows AND columns. It's like a spreadsheet for your webpage, where you decide how big each cell is.",
        "analogy": "If flexbox is a shelf (one direction), CSS Grid is a whole wall unit with shelves AND columns. You define the grid, then place items into specific cells or let them flow automatically.",
        "detailed_definition": "CSS Grid Layout creates two-dimensional grid-based layouts. The grid container (display: grid) defines rows (grid-template-rows), columns (grid-template-columns), and gaps. Items can span multiple rows/columns, be placed explicitly (grid-column, grid-row) or flow automatically (grid-auto-flow).",
        "advanced_definition": "Grid supports named lines, named areas (grid-template-areas), minmax(), repeat(), auto-fill/auto-fit for responsive grids without media queries. Subgrid inherits parent grid tracks. Grid items participate in both row and column axes simultaneously. The implicit grid handles overflow items. fr units distribute fractional remaining space.",
        "example": ".page {\n  display: grid;\n  grid-template-columns: 250px 1fr 250px;  /* sidebar, main, sidebar */\n  grid-template-rows: auto 1fr auto;       /* header, content, footer */\n  gap: 20px;\n}\n\nIn Webflow, Grid is available as a layout option.\nThose grid settings you configure? All CSS Grid.",
        "difficulty_tier": 2, "prerequisites": '["CSS", "flexbox"]'
    },
    {
        "domain_id": 3, "term": "responsive design",
        "simple_definition": "Responsive design means your website looks good on any screen size, from phone to desktop. It adapts and rearranges itself based on how much space it has.",
        "analogy": "Responsive design is like water. Pour it in a glass, it takes the shape of a glass. Pour it in a bowl, it takes the shape of a bowl. Your website flows to fill whatever container (screen) it's in.",
        "detailed_definition": "Responsive web design uses fluid grids, flexible images, and media queries to adapt layouts to different viewport sizes. Media queries apply styles conditionally based on screen width, height, or other features. Modern approaches also use fluid typography (clamp()), container queries, and flexible units (%, vw, vh, rem).",
        "advanced_definition": "Mobile-first CSS writes base styles for small screens, then adds complexity via min-width media queries. Container queries (@container) scope responsiveness to parent size, not viewport. Fluid typography uses clamp(min, preferred, max) for smooth scaling. Intrinsic design combines fluid units, minmax(), and auto-fit for layouts that respond without breakpoints.",
        "example": "/* Base (mobile) */\n.grid { display: flex; flex-direction: column; }\n\n/* Tablet and up */\n@media (min-width: 768px) {\n  .grid { flex-direction: row; }\n}\n\nIn Webflow, the breakpoint icons (desktop, tablet, phone)\nlet you set different styles at each size.\nThat generates media queries like these.",
        "difficulty_tier": 2, "prerequisites": '["CSS", "flexbox"]'
    },
    # Domain 4: JavaScript Basics
    {
        "domain_id": 4, "term": "JavaScript",
        "simple_definition": "JavaScript is the programming language that makes websites interactive. HTML is the structure, CSS is the style, JavaScript is the behavior: clicks, animations, form validation, data loading.",
        "analogy": "If a website is a car: HTML is the frame and body, CSS is the paint job and interior, and JavaScript is the engine. It makes things actually DO stuff.",
        "detailed_definition": "JavaScript is a dynamic, interpreted programming language and one of the core technologies of the web. It runs in the browser (client-side) and on servers (Node.js). It handles DOM manipulation, event handling, HTTP requests, animations, and application logic. It supports object-oriented, functional, and event-driven programming paradigms.",
        "advanced_definition": "JavaScript follows the ECMAScript specification (ES2015+ adds classes, modules, async/await, etc.). It uses a single-threaded event loop with a microtask queue (Promises) and macrotask queue (setTimeout). The V8 engine (Chrome/Node) JIT-compiles to machine code. Web APIs extend the language in browsers. TypeScript adds static typing as a superset.",
        "example": "// Change text when a button is clicked\nconst button = document.querySelector('#myButton');\nbutton.addEventListener('click', () => {\n  document.querySelector('#greeting').textContent = 'Hello!';\n});\n\nIn Webflow, those Interactions you set up? Under the hood,\nWebflow generates JavaScript to make them work.",
        "difficulty_tier": 2, "prerequisites": '["HTML", "CSS"]'
    },
    {
        "domain_id": 4, "term": "variable",
        "simple_definition": "A variable is a named container that holds a value. You give it a name, put something in it, and use that name later to get the value back.",
        "analogy": "A variable is like a labeled jar. You write 'cookies' on the jar and put cookies inside. Later, when you say 'get me the cookies jar,' you get the cookies. You can also swap them out for brownies.",
        "detailed_definition": "In JavaScript, variables are declared with let (reassignable), const (not reassignable), or var (function-scoped, legacy). Variables store any type: strings, numbers, booleans, arrays, objects, functions, null, undefined. JavaScript is dynamically typed, so a variable's type can change.",
        "advanced_definition": "let and const are block-scoped and exist in the Temporal Dead Zone before their declaration. var is function-scoped and hoisted (initialized as undefined). const prevents reassignment but not mutation of objects/arrays. Closures capture variables by reference. WeakRef and FinalizationRegistry interact with garbage collection.",
        "example": "let name = 'Alex';         // can be changed later\nconst age = 30;            // cannot be reassigned\nlet score = 0;\n\nscore = score + 10;        // now score is 10\nscore = score + 5;         // now score is 15\n\nconsole.log(name);         // prints: Alex\nconsole.log(score);        // prints: 15",
        "difficulty_tier": 2, "prerequisites": '["JavaScript"]'
    },
    {
        "domain_id": 4, "term": "function",
        "simple_definition": "A function is a reusable block of code that does a specific job. You define it once, then call it whenever you need that job done. Functions can take inputs and give back outputs.",
        "analogy": "A function is like a recipe. You define the steps once ('How to Make Pasta'). Then anytime you want pasta, you follow the recipe. You can change ingredients (inputs) to get different results (outputs).",
        "detailed_definition": "Functions in JavaScript are first-class objects. They can be declared (function name()), expressed (const name = function()), or arrow-formed (const name = () => {}). Functions receive parameters, execute a body, and optionally return a value. They create their own scope and can form closures over outer variables.",
        "advanced_definition": "Functions are objects with a [[Call]] internal method. Arrow functions lexically bind 'this'. Generator functions (function*) yield values iteratively. Async functions return Promises. The arguments object (non-arrow) provides a legacy parameter list. Rest parameters (...args) are preferred. Function.prototype includes call(), apply(), bind() for 'this' manipulation.",
        "example": "// Define a function\nfunction greet(name) {\n  return 'Hello, ' + name + '!';\n}\n\n// Use it\ngreet('Alex');      // returns: 'Hello, Alex!'\ngreet('Claude');    // returns: 'Hello, Claude!'\n\n// Arrow function version\nconst double = (num) => num * 2;\ndouble(5);          // returns: 10",
        "difficulty_tier": 2, "prerequisites": '["variable"]'
    },
    # Domain 5: The Terminal
    {
        "domain_id": 5, "term": "terminal",
        "simple_definition": "The terminal is a text-based way to control your computer. Instead of clicking icons, you type commands. It's like texting your computer instructions.",
        "analogy": "The terminal is like a concierge desk. Instead of wandering through a hotel yourself, you tell the concierge exactly what you want and they make it happen instantly.",
        "detailed_definition": "A terminal (or command-line interface) provides text-based interaction with the operating system. On macOS, the default shell is zsh. Commands navigate the filesystem, run programs, manage processes, and automate tasks. Terminal-based tools are fundamental to software development workflows.",
        "advanced_definition": "The terminal emulator renders output from a shell process. Shells (bash, zsh, fish) interpret commands, manage environment variables, handle piping (|), redirection (>, >>), and job control (&, fg, bg). Shell scripts automate command sequences. tmux/screen multiplex sessions. POSIX defines portable shell behavior.",
        "example": "ls              # list files in current directory\ncd projects     # go into 'projects' folder\npwd             # print where you are right now\nmkdir new-site  # create a new folder\nopen .          # open current folder in Finder\n\nYou're using the terminal right now in Claude Code!",
        "difficulty_tier": 1, "prerequisites": "[]"
    },
    {
        "domain_id": 5, "term": "file path",
        "simple_definition": "A file path is the route to find a specific file on your computer, like a trail of folders. It's the address of a file within your computer's folder structure.",
        "analogy": "A file path is like a physical address: Country > State > City > Street > House. On your computer: Hard Drive > Users > you > Documents > file.txt.",
        "detailed_definition": "File paths describe a location in the filesystem hierarchy. Absolute paths start from root (/ on macOS/Linux, C:\\ on Windows). Relative paths start from the current directory. Special symbols: . (current directory), .. (parent directory), ~ (home directory). Path separators are / on macOS/Linux.",
        "advanced_definition": "Paths resolve through the VFS (Virtual File System) layer. Symbolic links create aliases. PATH environment variable lists directories searched for executables. Glob patterns (*.js, **/*.md) match multiple files. realpath() resolves symlinks and relative references. URL paths mirror filesystem paths by convention but are distinct.",
        "example": "Absolute: /Users/yourname/Documents/projects/\nRelative: ./projects/  (from the current folder)\n\n~  = your home folder (e.g. /Users/yourname)\n.  = current folder\n.. = go up one folder\n\nExample: cd ~/Documents/projects/my-site",
        "difficulty_tier": 1, "prerequisites": '["terminal"]'
    },
    # Domain 9: Git & Version Control
    {
        "domain_id": 9, "term": "Git",
        "simple_definition": "Git tracks every change you make to your code and lets you go back in time if something breaks. It also lets multiple people work on the same code without stepping on each other.",
        "analogy": "Git is like a save system in a video game. You can save your progress at any point (commit), go back to an earlier save if you mess up, and even branch off to try different paths without losing your main progress.",
        "detailed_definition": "Git is a distributed version control system that tracks changes to files over time. Each change set is stored as a commit with a unique hash, message, and pointer to its parent. Branches allow parallel development. Git stores the full history locally, enabling offline work and fast operations.",
        "advanced_definition": "Git uses a content-addressable filesystem. Objects (blobs, trees, commits, tags) are SHA-1 hashed. The DAG (directed acyclic graph) of commits enables branch/merge operations. The index (staging area) mediates between working tree and repository. Packfiles compress objects for transfer. Reflog tracks branch tip movements for recovery.",
        "example": "git add .                  # stage all changes\ngit commit -m 'Add nav'    # save a snapshot\ngit log                    # see history\ngit branch new-feature     # create a branch\ngit checkout new-feature   # switch to it\n\nYou're using Git in Claude Code right now.\nEvery commit you see in the log is a Git snapshot.",
        "difficulty_tier": 2, "prerequisites": '["terminal", "file path"]'
    },
    {
        "domain_id": 9, "term": "commit",
        "simple_definition": "A commit is a saved snapshot of your code at a specific moment. It records what changed, when, and includes a message describing the change.",
        "analogy": "A commit is like taking a photo of your desk at the end of each day. If you spill coffee on your papers tomorrow, you can look at yesterday's photo to see exactly what was there.",
        "detailed_definition": "A Git commit is an immutable snapshot of the staged changes (index) in a repository. Each commit contains a tree object (directory state), parent commit reference(s), author/committer info, timestamp, and message. Commits form a linked chain that constitutes the project history.",
        "advanced_definition": "Commits are SHA-1 hashed objects in Git's object database. A merge commit has multiple parents. Interactive rebase (rebase -i) rewrites commit history. Cherry-pick applies individual commits across branches. Commit signing (GPG/SSH) provides authorship verification. Conventional Commits standardize message format for automated tooling.",
        "example": "git commit -m 'Add contact form to homepage'\n\nThis creates a snapshot that records:\n- What files changed\n- What the changes were\n- When it happened\n- Your message explaining why\n\nYou can always go back to this exact state later.",
        "difficulty_tier": 2, "prerequisites": '["Git"]'
    },
    {
        "domain_id": 9, "term": "branch",
        "simple_definition": "A branch is a separate copy of your code where you can make changes without affecting the main version. When your changes are ready, you merge the branch back.",
        "analogy": "A branch is like a separate draft of an essay. You copy the original, experiment with changes in your draft, and if you like the result, you fold those changes back into the final version.",
        "detailed_definition": "A Git branch is a movable pointer to a commit. The default branch is usually 'main'. Creating a branch creates a new pointer without copying files. Switching branches updates the working tree to match that branch's latest commit. Merging combines branch histories. Feature branches isolate work until it's ready.",
        "advanced_definition": "Branches are refs stored in .git/refs/heads/. HEAD points to the current branch (detached HEAD points directly to a commit). Fast-forward merges move the branch pointer. Three-way merges create merge commits. Rebase replays commits onto a new base for linear history. Branch strategies (Git Flow, trunk-based) organize team workflows.",
        "example": "git branch feature/new-hero    # create branch\ngit checkout feature/new-hero   # switch to it\n# ... make changes ...\ngit commit -m 'New hero section'\ngit checkout main              # go back to main\ngit merge feature/new-hero     # bring changes in\n\nThe 'main' branch stays safe while you experiment.",
        "difficulty_tier": 2, "prerequisites": '["commit"]'
    },
]

# ── Commands ─────────────────────────────────────────────────────────────────

def cmd_init():
    """Create database and seed data."""
    conn = get_conn()
    conn.executescript(SCHEMA)

    # Seed user profile
    conn.execute(
        "INSERT OR IGNORE INTO user_profile (id, name) VALUES (1, 'User')"
    )

    # Seed domains
    for d in SEED_DOMAINS:
        conn.execute(
            "INSERT OR IGNORE INTO domains (id, name, sort_order, icon) VALUES (?, ?, ?, ?)",
            d,
        )

    # Seed concepts
    for c in SEED_CONCEPTS:
        conn.execute(
            """INSERT OR IGNORE INTO concepts
               (domain_id, term, simple_definition, analogy, detailed_definition,
                advanced_definition, example, difficulty_tier, prerequisites)
               VALUES (:domain_id, :term, :simple_definition, :analogy,
                       :detailed_definition, :advanced_definition, :example,
                       :difficulty_tier, :prerequisites)""",
            c,
        )

    # Create progress rows for all concepts
    conn.execute(
        """INSERT OR IGNORE INTO progress (concept_id, next_review)
           SELECT id, datetime('now') FROM concepts"""
    )

    # Create skill tree rows
    for d in SEED_DOMAINS:
        unlocked = 1 if d[0] <= 3 else 0  # first 3 domains unlocked
        conn.execute(
            "INSERT OR IGNORE INTO skill_tree (domain_id, unlocked) VALUES (?, ?)",
            (d[0], unlocked),
        )

    conn.commit()
    conn.close()

    print(json.dumps({"status": "ok", "message": "Database initialized and seeded."}))


def cmd_profile(args):
    """Get or set user profile."""
    conn = get_conn()
    if len(args) >= 2 and args[0] == "set":
        field = args[1]
        value = " ".join(args[2:]) if len(args) > 2 else ""
        allowed = {"name", "overall_level", "onboarding_complete", "streak_days",
                    "last_session_date", "total_sessions", "total_xp"}
        if field not in allowed:
            print(json.dumps({"error": f"Unknown field: {field}"}))
            return
        conn.execute(f"UPDATE user_profile SET {field} = ? WHERE id = 1", (value,))
        conn.commit()

    row = conn.execute("SELECT * FROM user_profile WHERE id = 1").fetchone()
    conn.close()
    print(json.dumps(dict(row)))


def cmd_concepts(args):
    """List or search concepts."""
    conn = get_conn()
    if args and args[0] == "search":
        query = " ".join(args[1:])
        rows = conn.execute(
            """SELECT c.*, d.name as domain_name, d.icon as domain_icon
               FROM concepts c JOIN domains d ON c.domain_id = d.id
               WHERE c.term LIKE ? OR c.simple_definition LIKE ?""",
            (f"%{query}%", f"%{query}%"),
        ).fetchall()
    elif args and args[0] == "get":
        term = " ".join(args[1:])
        row = conn.execute(
            """SELECT c.*, d.name as domain_name, d.icon as domain_icon,
                      p.confidence, p.explanation_level, p.times_seen,
                      p.times_correct, p.times_wrong, p.streak, p.next_review
               FROM concepts c
               JOIN domains d ON c.domain_id = d.id
               LEFT JOIN progress p ON p.concept_id = c.id
               WHERE LOWER(c.term) = LOWER(?)""",
            (term,),
        ).fetchone()
        conn.close()
        if row:
            print(json.dumps(dict(row)))
        else:
            print(json.dumps({"error": f"Concept not found: {term}"}))
        return
    elif args and args[0] == "list":
        domain = " ".join(args[1:]) if len(args) > 1 else None
        if domain:
            rows = conn.execute(
                """SELECT c.term, c.difficulty_tier, d.name as domain_name, d.icon,
                          p.confidence, p.explanation_level
                   FROM concepts c
                   JOIN domains d ON c.domain_id = d.id
                   LEFT JOIN progress p ON p.concept_id = c.id
                   WHERE LOWER(d.name) = LOWER(?)
                   ORDER BY c.difficulty_tier, c.term""",
                (domain,),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT c.term, c.difficulty_tier, d.name as domain_name, d.icon,
                          p.confidence, p.explanation_level
                   FROM concepts c
                   JOIN domains d ON c.domain_id = d.id
                   LEFT JOIN progress p ON p.concept_id = c.id
                   ORDER BY d.sort_order, c.difficulty_tier, c.term"""
            ).fetchall()
    else:
        rows = conn.execute(
            """SELECT c.term, c.difficulty_tier, d.name as domain_name, d.icon,
                      p.confidence, p.explanation_level
               FROM concepts c
               JOIN domains d ON c.domain_id = d.id
               LEFT JOIN progress p ON p.concept_id = c.id
               ORDER BY d.sort_order, c.difficulty_tier, c.term"""
        ).fetchall()

    conn.close()
    print(json.dumps([dict(r) for r in rows]))


def cmd_add_concept(args):
    """Add a new concept from JSON."""
    data = json.loads(" ".join(args))
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO concepts
           (domain_id, term, simple_definition, analogy, detailed_definition,
            advanced_definition, example, difficulty_tier, prerequisites)
           VALUES (:domain_id, :term, :simple_definition, :analogy,
                   :detailed_definition, :advanced_definition, :example,
                   :difficulty_tier, :prerequisites)""",
        data,
    )
    concept_id = cur.lastrowid
    conn.execute(
        "INSERT INTO progress (concept_id, next_review) VALUES (?, datetime('now'))",
        (concept_id,),
    )
    conn.commit()
    conn.close()
    print(json.dumps({"status": "ok", "concept_id": concept_id}))


def cmd_progress(args):
    """Get progress for a concept."""
    term = " ".join(args[1:]) if len(args) > 1 else " ".join(args)
    conn = get_conn()
    row = conn.execute(
        """SELECT p.*, c.term, c.domain_id, d.name as domain_name
           FROM progress p
           JOIN concepts c ON p.concept_id = c.id
           JOIN domains d ON c.domain_id = d.id
           WHERE LOWER(c.term) = LOWER(?)""",
        (term,),
    ).fetchone()
    conn.close()
    if row:
        print(json.dumps(dict(row)))
    else:
        print(json.dumps({"error": f"No progress found for: {term}"}))


def cmd_record(args):
    """Record a quiz attempt. SM-2 spaced repetition."""
    if len(args) < 2:
        print(json.dumps({"error": "Usage: record <term> <correct|wrong>"}))
        return

    result = args[-1].lower()
    term = " ".join(args[:-1])

    if result not in ("correct", "wrong"):
        print(json.dumps({"error": "Result must be 'correct' or 'wrong'"}))
        return

    conn = get_conn()
    row = conn.execute(
        """SELECT p.*, c.id as cid, c.domain_id
           FROM progress p
           JOIN concepts c ON p.concept_id = c.id
           WHERE LOWER(c.term) = LOWER(?)""",
        (term,),
    ).fetchone()

    if not row:
        print(json.dumps({"error": f"Concept not found: {term}"}))
        conn.close()
        return

    p = dict(row)
    now = datetime.now(timezone.utc)

    p["times_seen"] += 1

    if result == "correct":
        p["times_correct"] += 1
        p["streak"] += 1

        # SM-2: increase interval
        if p["interval_days"] == 0:
            p["interval_days"] = 1
        elif p["interval_days"] == 1:
            p["interval_days"] = 6
        else:
            p["interval_days"] = p["interval_days"] * p["ease_factor"]

        p["ease_factor"] = max(1.3, p["ease_factor"] + 0.1)

        # XP
        xp_gain = 10 + (p["streak"] * 2)
        conn.execute(
            "UPDATE user_profile SET total_xp = total_xp + ? WHERE id = 1",
            (xp_gain,),
        )
        conn.execute(
            "UPDATE skill_tree SET xp_earned = xp_earned + ? WHERE domain_id = ?",
            (xp_gain, p["domain_id"]),
        )
    else:
        p["times_wrong"] += 1
        p["streak"] = 0
        p["interval_days"] = 1  # reset
        p["ease_factor"] = max(1.3, p["ease_factor"] - 0.2)

    # Confidence: weighted recent performance
    if p["times_seen"] > 0:
        p["confidence"] = round(p["times_correct"] / p["times_seen"], 3)

    # Auto-adjust explanation level based on confidence
    if p["confidence"] >= 0.85:
        p["explanation_level"] = 4
    elif p["confidence"] >= 0.6:
        p["explanation_level"] = 3
    elif p["confidence"] >= 0.3:
        p["explanation_level"] = 2
    else:
        p["explanation_level"] = 1

    next_review = now + timedelta(days=p["interval_days"])

    conn.execute(
        """UPDATE progress SET
           confidence = ?, explanation_level = ?, times_seen = ?,
           times_correct = ?, times_wrong = ?, last_reviewed = ?,
           next_review = ?, ease_factor = ?, interval_days = ?, streak = ?
           WHERE concept_id = ?""",
        (
            p["confidence"], p["explanation_level"], p["times_seen"],
            p["times_correct"], p["times_wrong"], now.isoformat(),
            next_review.isoformat(), p["ease_factor"], p["interval_days"],
            p["streak"], p["cid"],
        ),
    )

    # Check for skill tree level-ups
    st = conn.execute(
        "SELECT * FROM skill_tree WHERE domain_id = ?", (p["domain_id"],)
    ).fetchone()
    if st and st["xp_earned"] >= st["xp_required"] and st["level"] < 5:
        new_level = st["level"] + 1
        new_req = st["xp_required"] + (new_level * 50)
        conn.execute(
            "UPDATE skill_tree SET level = ?, xp_required = ? WHERE domain_id = ?",
            (new_level, new_req, p["domain_id"]),
        )
        # Unlock next domain if exists
        conn.execute(
            "UPDATE skill_tree SET unlocked = 1 WHERE domain_id = ?",
            (p["domain_id"] + 1,),
        )

    conn.commit()
    conn.close()

    print(json.dumps({
        "status": "ok",
        "term": term,
        "result": result,
        "confidence": p["confidence"],
        "explanation_level": p["explanation_level"],
        "streak": p["streak"],
        "next_review": next_review.isoformat(),
        "interval_days": round(p["interval_days"], 1),
    }))


def cmd_due(args):
    """Get concepts due for review."""
    limit = int(args[0]) if args else 10
    conn = get_conn()
    rows = conn.execute(
        """SELECT c.term, c.difficulty_tier, d.name as domain_name, d.icon,
                  p.confidence, p.explanation_level, p.next_review, p.streak,
                  p.times_seen
           FROM progress p
           JOIN concepts c ON p.concept_id = c.id
           JOIN domains d ON c.domain_id = d.id
           JOIN skill_tree st ON st.domain_id = d.id
           WHERE p.next_review <= datetime('now') AND st.unlocked = 1
           ORDER BY p.confidence ASC, p.next_review ASC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    print(json.dumps([dict(r) for r in rows]))


def cmd_stats():
    """Return overall stats."""
    conn = get_conn()
    profile = dict(conn.execute("SELECT * FROM user_profile WHERE id = 1").fetchone())
    total = conn.execute("SELECT COUNT(*) as cnt FROM concepts").fetchone()["cnt"]
    seen = conn.execute(
        "SELECT COUNT(*) as cnt FROM progress WHERE times_seen > 0"
    ).fetchone()["cnt"]
    mastered = conn.execute(
        "SELECT COUNT(*) as cnt FROM progress WHERE confidence >= 0.85"
    ).fetchone()["cnt"]
    learning = conn.execute(
        "SELECT COUNT(*) as cnt FROM progress WHERE confidence > 0 AND confidence < 0.85"
    ).fetchone()["cnt"]
    due_count = conn.execute(
        "SELECT COUNT(*) as cnt FROM progress WHERE next_review <= datetime('now')"
    ).fetchone()["cnt"]

    # Weakest concepts
    weak = conn.execute(
        """SELECT c.term, d.icon, p.confidence
           FROM progress p JOIN concepts c ON p.concept_id = c.id
           JOIN domains d ON c.domain_id = d.id
           WHERE p.times_seen > 0 AND p.confidence < 0.6
           ORDER BY p.confidence ASC LIMIT 5"""
    ).fetchall()

    # Domain breakdown
    domains = conn.execute(
        """SELECT d.name, d.icon, st.level, st.xp_earned, st.xp_required, st.unlocked,
                  COUNT(c.id) as concept_count,
                  SUM(CASE WHEN p.confidence >= 0.85 THEN 1 ELSE 0 END) as mastered_count
           FROM domains d
           LEFT JOIN skill_tree st ON st.domain_id = d.id
           LEFT JOIN concepts c ON c.domain_id = d.id
           LEFT JOIN progress p ON p.concept_id = c.id
           GROUP BY d.id
           ORDER BY d.sort_order"""
    ).fetchall()

    conn.close()

    print(json.dumps({
        "profile": profile,
        "total_concepts": total,
        "concepts_seen": seen,
        "concepts_mastered": mastered,
        "concepts_learning": learning,
        "due_for_review": due_count,
        "weakest": [dict(w) for w in weak],
        "domains": [dict(d) for d in domains],
    }))


def cmd_skill_tree():
    """Return full skill tree state."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT d.name, d.icon, d.sort_order, st.level, st.xp_earned,
                  st.xp_required, st.unlocked,
                  COUNT(c.id) as total_concepts,
                  SUM(CASE WHEN p.times_seen > 0 THEN 1 ELSE 0 END) as seen,
                  SUM(CASE WHEN p.confidence >= 0.85 THEN 1 ELSE 0 END) as mastered
           FROM domains d
           LEFT JOIN skill_tree st ON st.domain_id = d.id
           LEFT JOIN concepts c ON c.domain_id = d.id
           LEFT JOIN progress p ON p.concept_id = c.id
           GROUP BY d.id
           ORDER BY d.sort_order"""
    ).fetchall()
    conn.close()
    print(json.dumps([dict(r) for r in rows]))


def cmd_session(args):
    """Start or end a session."""
    if not args:
        print(json.dumps({"error": "Usage: session start <type> | session end <id> <asked> <correct>"}))
        return

    conn = get_conn()
    if args[0] == "start":
        session_type = args[1] if len(args) > 1 else "general"
        cur = conn.execute(
            "INSERT INTO sessions (type) VALUES (?)", (session_type,)
        )
        session_id = cur.lastrowid
        conn.execute(
            "UPDATE user_profile SET total_sessions = total_sessions + 1, last_session_date = date('now') WHERE id = 1"
        )
        conn.commit()
        conn.close()
        print(json.dumps({"status": "ok", "session_id": session_id}))
    elif args[0] == "end":
        if len(args) < 4:
            print(json.dumps({"error": "Usage: session end <id> <asked> <correct>"}))
            conn.close()
            return
        sid, asked, correct = int(args[1]), int(args[2]), int(args[3])
        conn.execute(
            """UPDATE sessions SET ended_at = datetime('now'),
               questions_asked = ?, questions_correct = ? WHERE id = ?""",
            (asked, correct, sid),
        )
        conn.commit()
        conn.close()
        print(json.dumps({"status": "ok", "session_id": sid}))
    else:
        conn.close()
        print(json.dumps({"error": f"Unknown session command: {args[0]}"}))


def cmd_next_lesson():
    """Recommend next concept to learn."""
    conn = get_conn()

    # Priority 1: unseen concepts in unlocked domains, lowest difficulty first
    row = conn.execute(
        """SELECT c.term, c.difficulty_tier, d.name as domain_name, d.icon,
                  c.simple_definition, c.prerequisites
           FROM concepts c
           JOIN domains d ON c.domain_id = d.id
           JOIN skill_tree st ON st.domain_id = d.id
           LEFT JOIN progress p ON p.concept_id = c.id
           WHERE st.unlocked = 1 AND (p.times_seen = 0 OR p.times_seen IS NULL)
           ORDER BY d.sort_order ASC, c.difficulty_tier ASC
           LIMIT 1"""
    ).fetchone()

    if row:
        conn.close()
        result = dict(row)
        result["reason"] = "new_concept"
        print(json.dumps(result))
        return

    # Priority 2: concepts due for review with lowest confidence
    row = conn.execute(
        """SELECT c.term, c.difficulty_tier, d.name as domain_name, d.icon,
                  p.confidence, p.explanation_level
           FROM progress p
           JOIN concepts c ON p.concept_id = c.id
           JOIN domains d ON c.domain_id = d.id
           WHERE p.next_review <= datetime('now')
           ORDER BY p.confidence ASC
           LIMIT 1"""
    ).fetchone()

    if row:
        conn.close()
        result = dict(row)
        result["reason"] = "review_due"
        print(json.dumps(result))
        return

    conn.close()
    print(json.dumps({"reason": "all_caught_up", "message": "All concepts reviewed and none due. Great work!"}))


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No command provided. Commands: init, profile, concepts, add-concept, progress, record, due, stats, skill-tree, session, next-lesson"}))
        sys.exit(1)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    commands = {
        "init": lambda: cmd_init(),
        "profile": lambda: cmd_profile(args),
        "concepts": lambda: cmd_concepts(args),
        "add-concept": lambda: cmd_add_concept(args),
        "progress": lambda: cmd_progress(args),
        "record": lambda: cmd_record(args),
        "due": lambda: cmd_due(args),
        "stats": lambda: cmd_stats(),
        "skill-tree": lambda: cmd_skill_tree(),
        "session": lambda: cmd_session(args),
        "next-lesson": lambda: cmd_next_lesson(),
    }

    if cmd in commands:
        try:
            commands[cmd]()
        except Exception as e:
            print(json.dumps({"error": str(e)}))
            sys.exit(1)
    else:
        print(json.dumps({"error": f"Unknown command: {cmd}"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
