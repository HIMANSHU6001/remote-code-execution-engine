import { lamaticClient } from "@/lib/lamatic";
import { NextResponse } from "next/server";

export async function POST(req: Request) {
    try {
        const payload = await req.json();

        if (!process.env.LAMATIC_FLOW_ID) {
            throw new Error("LAMATIC_FLOW_ID is not set");
        }
        console.log("LAMATIC FLOW EXECUTION");
        const response = await lamaticClient.executeFlow(process.env.LAMATIC_FLOW_ID, payload);
        console.log("LAMATIC RAW RESPONSE RECEIVED:");
        console.log(JSON.stringify(response, null, 2));

        return NextResponse.json(response);
    } catch (error: any) {
        console.error("Lamatic API Error:", error);
        return NextResponse.json({ error: error.message || "Internal Server Error" }, { status: 500 });
    }
}
