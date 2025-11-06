"""
Layout Component.

Manages page layout and structure.
"""

import streamlit as st


class PageLayout:
    """Manages the overall page layout."""

    def __init__(
        self,
        page_title: str = "PDF 讲解流 · Gemini 2.5 Pro",
        layout: str = "wide",
        initial_sidebar_state: str = "expanded"
    ):
        """
        Initialize page layout.

        Args:
            page_title: Title of the page
            layout: Layout mode (wide, center)
            initial_sidebar_state: Initial sidebar state
        """
        self.page_title = page_title
        self.layout = layout
        self.initial_sidebar_state = initial_sidebar_state

    def setup(self) -> None:
        """Setup the page configuration."""
        st.set_page_config(
            page_title=self.page_title,
            layout=self.layout,
            initial_sidebar_state=self.initial_sidebar_state
        )

    def render_header(self, subtitle: str = None) -> None:
        """
        Render page header.

        Args:
            subtitle: Optional subtitle
        """
        st.title(self.page_title)

        if subtitle:
            st.caption(subtitle)

        # Add separator
        st.markdown("---")

    def create_columns(
        self,
        count: int,
        ratios: list = None
        ) -> list:
        """
        Create columns with optional ratios.

        Args:
            count: Number of columns
            ratios: List of column ratios

        Returns:
            List of column objects
        """
        if ratios:
            return st.columns(ratios)
        else:
            return st.columns(count)

    def render_info_box(
        self,
        message: str,
        style: str = "info"
    ) -> None:
        """
        Render an info box.

        Args:
            message: Message to display
            style: Box style (info, success, warning, error)
        """
        if style == "info":
            st.info(message)
        elif style == "success":
            st.success(message)
        elif style == "warning":
            st.warning(message)
        elif style == "error":
            st.error(message)

    def render_metric_row(
        self,
        metrics: list,
        use_container_width: bool = True
    ) -> None:
        """
        Render a row of metrics.

        Args:
            metrics: List of metric dictionaries with keys:
                     'label', 'value', 'delta' (optional)
            use_container_width: Whether to use full container width
        """
        cols = st.columns(len(metrics))

        for col, metric in zip(cols, metrics):
            with col:
                if "delta" in metric:
                    st.metric(
                        label=metric["label"],
                        value=metric["value"],
                        delta=metric["delta"]
                    )
                else:
                    st.metric(
                        label=metric["label"],
                        value=metric["value"]
                    )

    def create_tabs(
        self,
        tab_names: list,
        tab_contents: list = None
        ):
        """
        Create tabs with content.

        Args:
            tab_names: List of tab names
            tab_contents: List of content functions (optional)

        Returns:
            List of tab objects
        """
        tabs = st.tabs(tab_names)

        if tab_contents:
            for tab, content_func in zip(tabs, tab_contents):
                with tab:
                    content_func()

        return tabs

    def render_section(
        self,
        title: str,
        content_func,
        divider: bool = True
    ):
        """
        Render a section with title and content.

        Args:
            title: Section title
            content_func: Function to render content
            divider: Whether to add divider after content
        """
        st.subheader(title)
        content_func()

        if divider:
            st.markdown("---")

    def render_expander_section(
        self,
        title: str,
        content_func,
        expanded: bool = False
    ):
        """
        Render an expandible section.

        Args:
            title: Section title
            content_func: Function to render content
            expanded: Whether initially expanded
        """
        with st.expander(title, expanded=expanded):
            content_func()

    def add_footer(self) -> None:
        """Add page footer."""
        st.markdown("---")
        st.caption(
            "Powered by Gemini 2.5 Pro | "
            "Made with ❤️ using Streamlit"
        )


class DashboardLayout(PageLayout):
    """Dashboard-specific layout."""

    def __init__(self, **kwargs):
        """Initialize dashboard layout."""
        super().__init__(**kwargs)

    def render_dashboard(
        self,
        header_func,
        metrics_func,
        main_content_func,
        sidebar_func = None
    ) -> None:
        """
        Render complete dashboard layout.

        Args:
            header_func: Header rendering function
            metrics_func: Metrics rendering function
            main_content_func: Main content rendering function
            sidebar_func: Sidebar rendering function (optional)
        """
        # Header
        header_func()

        # Metrics row
        metrics_func()

        # Main content
        main_content_func()

        # Footer
        self.add_footer()


class ComparisonLayout(PageLayout):
    """Layout for comparison views."""

    def __init__(self, **kwargs):
        """Initialize comparison layout."""
        super().__init__(**kwargs)

    def render_comparison(
        self,
        title_a: str,
        content_a_func,
        title_b: str,
        content_b_func
    ):
        """
        Render side-by-side comparison.

        Args:
            title_a: Title for left side
            content_a_func: Content function for left side
            title_b: Title for right side
            content_b_func: Content function for right side
        """
        col1, col2 = st.columns(2)

        with col1:
            st.subheader(title_a)
            content_a_func()

        with col2:
            st.subheader(title_b)
            content_b_func()


class WizardLayout(PageLayout):
    """Multi-step wizard layout."""

    def __init__(self, steps: list, **kwargs):
        """
        Initialize wizard layout.

        Args:
            steps: List of step names
        """
        super().__init__(**kwargs)
        self.steps = steps
        self.current_step = 0

    def render_step_indicator(self) -> None:
        """Render step indicator."""
        st.progress(self.current_step / (len(self.steps) - 1))

        # Show step names
        for i, step in enumerate(self.steps):
            if i == self.current_step:
                st.markdown(f"**{i+1}. {step}** (当前)")
            elif i < self.current_step:
                st.markdown(f"✅ {i+1}. {step} (已完成)")
            else:
                st.markdown(f"⏳ {i+1}. {step} (等待中)")

    def render_step(
        self,
        step_index: int,
        content_func
    ) -> bool:
        """
        Render a single step.

        Args:
            step_index: Step index
            content_func: Content rendering function

        Returns:
            True if step completed successfully
        """
        self.current_step = step_index

        # Show indicator
        self.render_step_indicator()

        # Show content
        st.markdown(f"### 步骤 {step_index + 1}: {self.steps[step_index]}")
        content_func()

        # Navigation
        cols = st.columns([1, 1, 4])

        with cols[0]:
            if step_index > 0:
                if st.button("⬅️ 上一步", key=f"prev_{step_index}"):
                    self.current_step = step_index - 1
                    st.rerun()

        with cols[1]:
            if step_index < len(self.steps) - 1:
                if st.button("下一步 ➡️", key=f"next_{step_index}"):
                    self.current_step = step_index + 1
                    st.rerun()

        return True
