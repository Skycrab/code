
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.Signature;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.annotation.Pointcut;
import org.aspectj.lang.reflect.MethodSignature;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.EnableAspectJAutoProxy;

import java.lang.reflect.Method;

@Aspect
@EnableAspectJAutoProxy(proxyTargetClass = true)
@Configuration
public class LogAspect {
    private static final Logger logger = LoggerFactory.getLogger(LogAspect.class);

    @Pointcut("@annotation(org.springframework.web.bind.annotation.PostMapping)")
    public void postMappingPointCut() {}

    @Pointcut("@annotation(org.springframework.web.bind.annotation.GetMapping)")
    public void getMappingPointCut() {}

    @Pointcut("@annotation(org.springframework.web.bind.annotation.RequestMapping)")
    public void requestMappingPointCut() {}

    @Pointcut("@annotation(org.springframework.web.bind.annotation.DeleteMapping)")
    public void deleteMappingPointCut() {}


    /**
     * 是否不记录结果集，部分如下载结果集应该不记录
     * @return
     */
    private boolean noLogResult(Signature signature) {
        try{
            MethodSignature methodSignature = (MethodSignature) signature;
            Method method = methodSignature.getMethod();
            return method.isAnnotationPresent(NoLogResult.class);
        }catch (Exception e) {
            logger.error("metric=noLogResult||signature={}||e=", signature.toString(), e);
            return false;
        }
    }

    @Around("postMappingPointCut() || getMappingPointCut() || requestMappingPointCut() || deleteMappingPointCut() ")
    public Object logControllerInAndOut(ProceedingJoinPoint joinPoint) throws Throwable {
        Object result;
        long start = System.currentTimeMillis();
        Signature signature = joinPoint.getSignature();
        String param = JsonUtil.toJson(joinPoint.getArgs());
        MdcUtil.start();
        try {
            result = joinPoint.proceed();
            long end = System.currentTimeMillis();
            if(noLogResult(signature)) {
                logger.info("method={}||execute_time={}||param={}", signature.toString(), end-start, param);
            }else {
                logger.info("method={}||execute_time={}||param={}||result={}", signature.toString(), end-start, param, JsonUtil.toJson(result));
            }
        }catch (Exception e) {
            long end = System.currentTimeMillis();
            result = ResponseUtil.fail();
            logger.error("method={}||execute_time={}||param={}||error=", signature.toString(), end-start, param, e);
        }
        MdcUtil.clear();
        return result;
    }

    @Pointcut("execution(* com.api.thrift..*.*(..))")
    public void thriftPointCut() {}

    @Around("thriftPointCut()")
    public Object thriftTraceId(ProceedingJoinPoint joinPoint) throws Throwable {
        MdcUtil.start();
        try{
            return joinPoint.proceed();
        }finally {
            MdcUtil.clear();
        }
    }
}
