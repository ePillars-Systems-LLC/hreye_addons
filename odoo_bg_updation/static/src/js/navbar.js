import { NavBar } from '@web/webclient/navbar/navbar';
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(NavBar.prototype, {
    setup() {
        super.setup?.();
        this.company = useService("company");
        console.log("===>", this)
        this.state.currentCompanyId = this.company?.currentCompany?.id;
    }
});
