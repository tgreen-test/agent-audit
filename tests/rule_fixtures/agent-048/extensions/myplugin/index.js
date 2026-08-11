// AGENT-048 trigger: extension importing core internals directly.
const registry = require('../../core/registry');
const secrets = require('../../core/secrets');

module.exports = { registry, secrets };
