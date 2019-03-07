
import org.slf4j.MDC;

import java.util.Map;

/**
 * @author yihaibo
 * @date 19/1/3
 * referer: https://github.com/ofpay/logback-mdc-ttl
 */

public class MdcUtil {
    public static void start() {
        String traceId = TaskUtil.uuid();
        MDC.put("trace_id",traceId);
    }


    public static void clear() {
        MDC.clear();
    }

    public static String getTraceId(){
        return MDC.get("trace_id");
    }

    public static void setContextMap(Map<String,String> contextMap){
        MDC.setContextMap(contextMap);
    }

    public static Map<String,String> getCurrentContextMap(){
        return MDC.getCopyOfContextMap();
    }
}
