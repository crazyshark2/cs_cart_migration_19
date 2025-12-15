odoo.define('cs_cart_migration.migration_progress', function (require) {
    "use strict";

    var FormController = require('web.FormController');
    var FormView = require('web.FormView');
    var viewRegistry = require('web.view_registry');

    var MigrationProgressController = FormController.extend({
        /**
         * @override
         */
        init: function (parent, model, renderer, params) {
            this._super.apply(this, arguments);
            this.progressCheckInterval = null;
        },

        /**
         * Start checking progress if migration is in progress
         */
        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                var record = self.model.get(self.handle);
                if (record && record.data.state === 'progress') {
                    self._startProgressChecker();
                }
            });
        },

        /**
         * Start interval to check progress
         */
        _startProgressChecker: function () {
            var self = this;
            this.progressCheckInterval = setInterval(function () {
                self._checkProgress();
            }, 3000); // Check every 3 seconds
        },

        /**
         * Check migration progress
         */
        _checkProgress: function () {
            var self = this;
            var record = self.model.get(self.handle);
            
            if (!record || record.data.state !== 'progress') {
                clearInterval(self.progressCheckInterval);
                return;
            }

            // Reload the record to get updated progress
            self.reload();
        },

        /**
         * Clean up interval on destroy
         */
        destroy: function () {
            if (this.progressCheckInterval) {
                clearInterval(this.progressCheckInterval);
            }
            this._super.apply(this, arguments);
        },
    });

    var MigrationProgressFormView = FormView.extend({
        config: _.extend({}, FormView.prototype.config, {
            Controller: MigrationProgressController,
        }),
    });

    viewRegistry.add('cs_cart_migration_progress_form', MigrationProgressFormView);
});