<template>
  <splitpanes class="default-theme">
    <pane size="20" :style="{ 'min-width': '300px' }">
      <report-filter
        v-fill-height
        :namespace="namespace"
        :show-remove-filtered-reports="false"
        :report-count="reportCount"
        :show-diff-type="false"
        :show-compare-to="showCompareTo"
        :refresh-filter="refreshFilterState"
        @refresh="refresh"
        @set-refresh-filter-state="setRefreshFilterState"
      />
    </pane>
    <pane>
      <div v-fill-height>
        <v-tabs
          v-model="tab"
        >
          <v-tab
            v-for="t in tabs"
            :key="t.name"
            :to="{ ...t.to, query: {
              ...$router.currentRoute.query
            }}"
            exact
          >
            <v-icon class="mr-2">
              {{ t.icon }}
            </v-icon>
            {{ t.name }}
          </v-tab>
        </v-tabs>

        <keep-alive>
          <router-view
            :bus="bus"
            :namespace="namespace"
            @refresh-filter="setRefreshFilterState(true)"
          />
        </keep-alive>
      </div>
    </pane>
  </splitpanes>
</template>

<script>
import Vue from "vue";
import { Pane, Splitpanes } from "splitpanes";
import { mapState } from "vuex";

import { ccService, handleThriftError } from "@cc-api";

import { FillHeight } from "@/directives";
import { ReportFilter } from "@/components/Report/ReportFilter";

const namespace = "statistics";

export default {
  name: "Statistics",
  components: {
    Splitpanes,
    Pane,
    ReportFilter
  },
  directives: { FillHeight },
  data() {
    const tabs = [
      {
        name: "Product Overview",
        icon: "mdi-briefcase-outline",
        to: { name: "product-overview" },
        showCompareTo: true
      },
      {
        name: "Checker Statistics",
        icon: "mdi-card-account-details",
        to: { name: "checker-statistics" },
        showCompareTo: true
      },
      {
        name: "Severity Statistics",
        icon: "mdi-speedometer",
        to: { name: "severity-statistics" },
        showCompareTo: true
      },
      {
        name: "Component Statistics",
        icon: "mdi-puzzle-outline",
        to: { name: "component-statistics" },
        showCompareTo: true
      },
      {
        name: "Checker Coverage",
        icon: "mdi-clipboard-check-outline",
        to: { name: "checker-coverage-statistics" },
        showCompareTo: false
      },
      {
        name: "Guideline Statistics",
        icon: "mdi-clipboard-text-outline",
        to: { name: "guideline-statistics" },
        showCompareTo: false
      },
    ];

    return {
      namespace: namespace,
      refreshFilterState: false,
      reportCount: 0,
      showCompareTo: true,
      tab: null,
      tabs: tabs,
      bus: new Vue(),

      // Map the tab link names to boolean values. If the value of a key is
      // true, it means that on the next tab change the tab needs to be
      // updated.
      refreshTabs: tabs.reduce((map, tab) => {
        const resolve = this.$router.resolve(tab.to);
        map[resolve.route.name] = false;

        return map;
      }, {})
    };
  },

  computed: {
    ...mapState({
      runIds(state, getters) {
        return getters[`${this.namespace}/getRunIds`];
      },
      reportFilter(state, getters) {
        return getters[`${this.namespace}/getReportFilter`];
      }
    })
  },

  watch: {
    /**
     * Refresh the current statistics tab if the tab is marked as true in the
     * refresh tab map.
     */
    tab() {
      if (!this.tab) return;

      this.showCompareTo = this.tabs.filter(
        tab => tab.showCompareTo
      ).map(
        tab => tab.to.name
      ).includes(
        this.$router.currentRoute.name
      );

      const resolve = this.$router.resolve(this.tab);
      if (this.refreshTabs[resolve.route.name]) {
        this.refreshCurrentTab();
      }
    }
  },

  methods: {
    refresh() {
      ccService.getClient().getRunResultCount(this.runIds,
        this.reportFilter, null, handleThriftError(res => {
          this.reportCount = res.toNumber();
        }));

      this.tabs.forEach(tab => {
        const resolve = this.$router.resolve(tab.to);
        this.refreshTabs[resolve.route.name] = true;
      });

      this.refreshCurrentTab();
    },

    /**
     * Refresh the current statistics tab.
     */
    refreshCurrentTab() {
      this.bus.$emit("refresh");

      const resolve = this.$router.resolve(this.tab);
      this.refreshTabs[resolve.route.name] = false;
    },

    setRefreshFilterState(state) {
      this.refreshFilterState=state;
    }
  }
};
</script>

<style lang="scss" scoped>
.splitpanes.default-theme {
  .splitpanes__pane {
    background-color: inherit;
  }
}
</style>
